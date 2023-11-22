#!/usr/bin/env python3

from getpass import getpass
import os
import sys
import subprocess
import logging
import time
from socket import *
import paramiko
from paramiko.channel import Channel
from paramiko.ssh_exception import AuthenticationException, SSHException

# Настройка логирования
logging.basicConfig(filename='log.txt',
                    format=u'%(asctime)s %(filename)s [LINE:%(lineno)d] [%(funcName)s()] #%(levelname)-15s %(message)s',
                    level=logging.INFO,
                    )

# Получение имени компьютера и текущего пользователя
this_host = subprocess.run(['hostname'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0]
user = subprocess.run(['whoami'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0]

# Ярлыки на сетевую папку
network_share = """[Desktop Entry]
Icon=folder-remote
Name=Задания
Type=Application
Exec=dolphin sftp://student@{admin_host}.local/home/share
"""
network_share_for_teacher = """[Desktop Entry]
Icon=folder-remote
Name=Задания
Type=Link
URL[$e]=/home/share
"""

# Ярлык veyon
veyon_link = """[Desktop Entry]
Version=1.0
Type=Application
Exec=/usr/bin/veyon-master
Icon=/usr/share/icons/hicolor/scalable/apps/veyon-master.svg
Terminal=false
Name=Veyon
Comment=Monitor and control remote computers
Comment[de]=Entfernte Computer beobachten und steuern
Comment[ru]=Наблюдение за удалёнными компьютерами и управление ими (veyon)
Categories=Qt;Education;Network;RemoteAccess;
Keywords=classroom,control,computer,room,lab,monitoring,admin,admin,student
"""

# Ярлык приложения "Собрать работы"
teacher_sh_link = f"""[Desktop Entry]
Icon=/usr/share/icons/breeze-dark/apps/48/rocs.svg
Name=Собрать работы
Type=Application
Exec=sh /home/teacher/teacher_control/teacher_control.sh
"""

# Ярлык на ssh-add для автозагрузки
ssh_add_link = """[Desktop Entry]
Exec=ssh-add
Icon=
Name=ssh-add
Path=
Terminal=False
Type=Application
"""


class SSHTimeoutError(Exception):
    # Таймаут ssh превышен
    pass


class WrongRootPass(Exception):
    # Неправильный пароль root
    pass


def exit_app():
    """
    Выход из приложения
    """
    logging.info("Выход из программы")
    print('Выход из программы...')
    sys.exit(0)


def ssh_copy_to_root(host, root_pass):
    """
    Копирование ключей ssh от admin в root
    :param host: имя или адрес хоста
    :param root_pass: пароль root на хосте
    :return: вывод результата от терминала
    """
    logging.info("Начало копирования ключей ssh to root")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=host, port=22, timeout=5, username='admin')
        logging.info(f"Подключено по ssh@admin без пароля к {host}")
    except AuthenticationException:
        print(f"Введите пароль учётной записи admin на {host}: ")
        admin_pass = str(input())
        ssh.connect(hostname=host, port=22, timeout=5, username='admin', password=admin_pass)
        logging.info(f"Подключено по ssh@admin С ПАРОЛЕМ к {host}")
    except timeout:
        logging.info(f"timeout Не удалось подключиться к ssh@admin к {host}")
        raise SSHTimeoutError
    except SSHException:
        print('Ошибка ssh')
        logging.info(f"SSHException Не удалось подключиться к ssh@admin к {host}")
        exit_app()
    channel: Channel = ssh.invoke_shell()
    channel_data = str()
    channel_data += str(channel.recv(999).decode('utf-8'))
    channel.send("su -\n")
    time.sleep(0.5)
    channel.send(f"{root_pass}\n")
    time.sleep(0.5)
    channel.send("cat /home/admin/.ssh/authorized_keys > /root/.ssh/authorized_keys\n")
    time.sleep(0.5)
    channel.send("exit\n")
    time.sleep(0.5)
    channel.send("exit\n")
    time.sleep(0.5)
    channel_data += f"{str(channel.recv(99999).decode('utf-8'))}\n"
    channel.close()
    ssh.close()
    logging.info(f"Результат работы paramiko: {channel_data}")
    return channel_data


def ping():
    """
    Подключение к хостам из hosts.txt и проверка ping
    :return: список хостов в случае успеха
    """
    try:
        with open("/home/admin/teacher_control/hosts.txt", "r") as hosts:
            list_of_hosts = hosts.readlines()
    except IOError:
        print(
            '\nСоздайте файл /home/admin/teacher_control/hosts.txt, перечислите в нём имена компьютеров построчно и '
            'запустите скрипт повторно')
        exit_app()
    if len(list_of_hosts) == 0 or list_of_hosts[0] == '':
        print('Заполните файл hosts.txt: перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
              '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local. '
              'Если по имени компьютеры не находятся, '
              'то используйте ip-адреса, но так делать не рекомендуется из-за смены адресов по DHCP.')
        exit_app()
    print("\nФайл hosts.txt найден, выполняю ping всех устройств:")
    errors = 0
    for host in list_of_hosts:
        host = host.split('\n')[0]
        result = subprocess.run(['ping', '-c1', host], stdout=subprocess.PIPE)
        if result.returncode == 0:
            print(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ")
            logging.info(f"ping: {host}: УСПЕШНОЕ СОЕДИНЕНИЕ {result=} {result.returncode=}")
        elif result.returncode == 2:
            logging.info(f"ping: {host}: {result=} {result.returncode=}")
            errors += 1
        else:
            print(host + " неизвестная ошибка")
            logging.info(host + f" неизвестная ошибка {result=} {result.returncode=}")
            errors += 1
    if errors > 0:
        print("Некоторые компьютеры найти не удалось, "
              "проверьте правильность имён или адресов в hosts.txt и повторите попытку.")
        exit_app()
    return list_of_hosts


def test_ssh():
    """
    Проверка подключения к хостам пользователем root
    """
    print("\nПроверяю доступ по ssh к компьютерам из hosts.txt:")
    list_of_hosts = ping()
    for host in list_of_hosts:
        host = host.split('\n')[0]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(hostname=host, port=22, timeout=5, username='root')
            logging.info(f"Подключено по ssh@root без пароля к {host}")
        except AuthenticationException:
            print('Не удалось подключиться по ssh к', host)
            logging.info(f"Не удалось подключиться по ssh@root без пароля к {host}")
            exit_app()
        ssh.close()


def setup_ssh():
    """
    Создание ключей ssh
    Копирование ключей на хосты для пользователя admin
    Подключение к хостам под пользователем admin и копирование ключей пользователю root
    """
    list_of_hosts = ping()
    logging.info(f"Начало создания ключа")
    print("\nСоздаю ключ ssh:")
    os.system("ssh-keygen -t ed25519 -q -P '' -f /home/admin/.ssh/id_ed25519")
    logging.info(f"Ключ создан")
    time.sleep(1)
    os.system('mkdir -p /home/admin/.config/autostart')
    with open('/home/admin/.config/autostart/ssh-add.desktop', 'w') as file_link:
        file_link.write(ssh_add_link)
    logging.info(f"Ярлык в автозапуск ss-add создан")
    logging.info(f"Начало копирования ключей")
    print('\nКопирую ключ на все компьютеры из списка hosts.txt:')
    os.system(
        "ssh-add; "
        "for i in $(cat /home/admin/teacher_control/hosts.txt); "
        "do ssh-copy-id -f -i /home/admin/.ssh/id_ed25519.pub admin@$i -o IdentitiesOnly=yes; "
        "done")
    logging.info(f"Ключи скопированы")
    print("Теперь я настрою ssh для суперпользователя на всех устройствах")
    print("Введите пароль учётной записи суперпользователя root (для устройств учеников): ")
    root_pass = str(getpass("root password:"))
    for host in list_of_hosts:
        host = host.split('\n')[0]
        print(f"Пробую подключиться к {host}")
        logging.info(f"Пробую подключиться к {host}")
        try:
            result = ssh_copy_to_root(host, root_pass)
            if "[root@" not in result:
                print(f'Пароль root на {host} не подошёл, введите ещё раз: ')
                logging.info(f'Пароль root на {host} не подошёл 1 попытка')
                root_pass2 = str(str(getpass(f"root@{host} password:")))
                result2 = ssh_copy_to_root(host, root_pass2)
                if "[root@" not in result2:
                    logging.info(f'Пароль root на {host} не подошёл 2 попытка')
                    raise WrongRootPass
        except (SSHTimeoutError, WrongRootPass):
            print(f"Не удалось подключиться к {host}")
            logging.info(f"Не удалось подключиться к {host}")
            break
        print(f"На {host} ssh для root настроен успешно")
        logging.info(f"На {host} ssh для root настроен успешно")


def install_veyon():
    """
    Установка и настройка veyon: скачивание пакета, создание ключей, копирование списка хостов и настройка по ssh на
    хостах
    """
    print("Введите номер этого кабинета:")
    kab = input()
    print(
        'Сначала установим на этом компьютере, введите пароль от root и ждите окончания установки: ')
    logging.info(f'Установка вейон на комьютере учителя')
    os.system(
        "su - root -c 'apt-get update -y; "
        "apt-get install veyon -y; "
        "veyon-cli authkeys delete admin/private; "
        "veyon-cli authkeys delete admin/public; "
        "veyon-cli authkeys create teacher; "
        "veyon-cli authkeys setaccessgroup teacher/private admin; "
        "veyon-cli authkeys setaccessgroup teacher/private teacher; "
        "veyon-cli authkeys export teacher/public /home/admin/teacher_control/teacher_public_key.pem; "
        "veyon-cli networkobjects add location {}; "
        "for i in $(cat /home/admin/teacher_control/hosts.txt); "
        "do veyon-cli networkobjects add computer $i $i \"\" {}; "
        "done; "
        "veyon-cli config export /home/admin/teacher_control/myconfig.json; "
        "veyon-cli service start'".format(kab, kab)
    )
    logging.info(f'Установка вейон на комьютере учителя УСПЕШНО')
    print("Настраиваю veyon на компьютерах учеников (должен быть доступ к root по ssh):")
    logging.info(f'Установка вейон на комьютере учеников')
    os.system(
        'ssh-add; '
        'for i in $(cat /home/admin/teacher_control/hosts.txt); '
        'do scp /home/admin/teacher_control/teacher_public_key.pem root@$i:/tmp/ && '
        'scp /home/admin/teacher_control/myconfig.json root@$i:/tmp/ && '
        'ssh root@$i "apt-get update && '
        'apt-get -y install veyon && '
        'veyon-cli authkeys delete admin/public; '
        'veyon-cli authkeys import teacher/public /tmp/teacher_public_key.pem && '
        'veyon-cli config import /tmp/myconfig.json && '
        'veyon-cli service start && '
        'reboot"; '
        'done'
    )
    logging.info(f'Установка вейон на комьютере учеников УСПЕШНО')
    print("Создаю ярлык:")
    var =  "su - root -c 'echo \""+veyon_link+"\" > /home/teacher/Рабочий\ стол/veyon.desktop'"
    os.system (var)
    print('Veyon установлен')
    logging.info('Veyon установлен')

def wol_on():
    """
    Включение Wake-On-Lan
    """
    print('Включаю WOL')
    logging.info('Включение WOL')
    os.system('sudo echo ACTION=="add", SUBSYSTEM=="net", NAME=="en*", RUN+="/usr/sbin/ethtool -s $name wol g" >> /etc/udev/rules.d/81-wol.rules ')
    print('WOL включен')
    logging.info('Включили WOL')

def teacher_control_store():
    """
    Копирование программы для сбора работ и создание ярлыка
    """
    os.system('sudo mkdir -p /home/teacher/teacher_control')
    os.system("sudo cp teacher_control.sh /home/teacher/teacher_control")
    print('Скрипт teacher_control сохранён')

    var =  "su - root -c 'echo \""+teacher_sh_link+"\" > /home/teacher/Рабочий\ стол/teacher Control.desktop'"
    os.system (var)

    print('Успешно создан ярлык для teacher_control')
    logging.info('Успешно создан ярлык для teacher_control')


def student_archive():
    """
    Подключение по ssh к хостам и создание архива /home/student
    """
    print("Начинаю сохранение папки student на всех устройствах в архив:")
    logging.info("Начинаю сохранение папки student на всех устройствах в архив")
    os.system(
        "ssh-add; for i in $(cat /home/admin/teacher_control/hosts.txt); "
        "do ssh root@$i 'mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && "
        "chmod 777 /home/student/Рабочий\ стол/Сдать\ работы && "
        "cd /home && "
        "pkill -u student; "
        "echo \"sleep 5 && tar cfz student.tar.gz student && reboot\" | at now'; done")
    print('Архивы созданы\nВведите пароль root на этом компьютере: ')
    logging.info('Архивы созданы')
    teacher_control_store()


def network_folders():
    """
    Создание сетевой папки и копирование ярлыка по ssh на хосты
    """
    logging.info("Создание сетевой папки")
    print(
        'Создаю сетевую папку share в /home/ и отправлю ссылку на компы учеников и рабочий стол учителя, '
        'введите пароль суперпользователя на этом компьютере: ')
    os.system(
        "su - root -c 'mkdir /home/share && chmod 777 -R /home/share && chown teacher /home/share;"
        "touch /home/teacher/Рабочий\ стол/share.desktop'")
    with open('share.desktop', 'w') as file_link:
        file_link.write(network_share.format(admin_host=this_host))
        file_link.close()

    os.system(
        'ssh-add; '
        'for i in $(cat /home/admin/teacher_control/hosts.txt); '
        'do scp share.desktop root@$i:"/home/student/Рабочий\\ стол"; '
        'done')
    var =  "su - root -c 'echo \""+network_share_for_teacher+"\" >> /home/teacher/Рабочий\ стол/share.desktop'"
    os.system (var)

    print('Сетевая папка создана')
    logging.info('Сетевая папка создана')

def sudo_admin():
    """
    Включение sudo и добавление уз admin в sudoers 
    """
    logging.info("Настройка Sudoers")
    print("Настраиваю Sudoers")
    os.system(
        "su - root -c 'sed '25s/^#//' -i /etc/sudoers && sed '94s/^#//' -i /etc/sudoers && "
        "sed '100s/^#//' -i /etc/sudoers && "
        "control sudowheel enabled'"
        )
    os.system(
        "su - root -c 'echo admin ALL=\(ALL\)\ ALL >> /etc/sudoers'"
        )
    print("Sudoers настроен")
    logging.info("Sudoers настроен")

def resolve_hostname():
    """
    Настройка резолва имён линухи на винде. Сначала учитель, потом ученики
    """
    os.system(    
        "su - root -c 'apt-get update;"
        "apt-get install samba -y;"
        "systemctl enable smb.service;"
        "systemctl enable nmb.service;"
        "systemctl enable winbind.service;"
        "service smb start;"
        "service nmb start;"
        "service winbind start'"
    )
    logging.info("Самба сервисы установлены и запущены на ПК учителя")
    print('Настройка Учителя завершена, начинаю настройку учеников')
    os.system(
        'ssh-add; '
        'for i in $(cat /home/admin/teacher_control/hosts.txt); '
        'do ssh root@$i "apt-get update;'
        'apt-get install samba -y;'
        'systemctl enable smb.service;'
        'systemctl enable nmb.service;'
        'systemctl enable winbind.service;'
        'service smb start;'
        'service nmb start;'
        'service winbind start;'
        'reboot"; '
        'done'
    )
    logging.info("Самба сервисы установлены и запущены на ПК ученика")
    print('Установка завершена')

def FuckYouCCO():
    print('Сносим ЦЦОшные излишки у учителя')
    os.system(
        "su - root -c 'apt-get remove apt-indicator uds-system-agent mos-tele -y && rm -f /etc/uds-system-agent/*;"
    )
    logging.info("На ПК учителя удалён apt-indicator uds-system-agent mos-tele")
    print('Сносим ЦЦОшные излишки у учеников')
    os.system(
        "ssh-add;"
        "for i in $(cat /home/admin/teacher_control/hosts.txt);"
        "do ssh root@$i 'apt-get remove apt-indicator uds-system-agent mos-tele -y && rm -f /etc/uds-system-agent/*"
        "done"
    )
    logging.info("На ПК учеников удалён apt-indicator uds-system-agent mos-tele")

def wine_install():
    print('Ставим Wine на учительском ПК')
    os.system(
        "rm -rf /etc/apt/sources.list.d/mos-base-repo.list;"
        "rm -rf /etc/apt/sources.list.d/mos-repo.list;"
        "sed '4s/^#//' -i /etc/apt/sources.list.d/alt.list;"
        "sed '5s/^#//' -i /etc/apt/sources.list.d/alt.list;"
        "sed '6s/^#//' -i /etc/apt/sources.list.d/alt.list;"
        "su - root -c 'apt-get update --fix-missing;"
        "apt-get install i586-wine fonts-ttf-wingdings wine-programs i586-libGL i586-libGLU winewizard i586-playonlinux i586-xorg-dri-vmwgfx i586-xorg-dri-virtio i586-xorg-dri-swrast i586-xorg-dri-radeon i586-xorg-dri-nouveau i586-xorg-dri-intel wine-mono winetricks -y; "
        "dpkg --add-architecture i386; "
        "rm -R -I ~/.wine -y --force;"
        "env WINEPREFIX=~/.wine WINEARCH=win32 winecfg';"
        "su - teacher -c 'rm -R -I ~/.wine --force;"
        "env WINEPREFIX=~/.wine WINEARCH=win32 winecfg;"
        "winetricks --force -q dotnet472;"
        "winetricks -q d3dcompiler_47;"
        "winetricks -q vcrun2015;"
        "winetricks -q corefonts'"
        "done"
    )
    logging.info('Wine на учительском ПК установлен')
    print('Ставим Wine на ученических ПК')
    os.system(
        "ssh-add;"
        "for i in $(cat /home/admin/teacher_control/hosts.txt);"
        "do ssh root@$i 'apt-get update --fix-missing;"
        "rm -rf /etc/apt/sources.list.d/mos-base-repo.list;"
        "rm -rf /etc/apt/sources.list.d/mos-repo.list;"
        "sed '4s/^#//' -i /etc/apt/sources.list.d/alt.list;"
        "sed '5s/^#//' -i /etc/apt/sources.list.d/alt.list;"
        "sed '6s/^#//' -i /etc/apt/sources.list.d/alt.list;"
        "apt-get install i586-wine fonts-ttf-wingdings wine-programs i586-libGL i586-libGLU winewizard i586-playonlinux i586-xorg-dri-vmwgfx i586-xorg-dri-virtio i586-xorg-dri-swrast i586-xorg-dri-radeon i586-xorg-dri-nouveau i586-xorg-dri-intel wine-mono winetricks -y;"
        "dpkg --add-architecture i386;"
        "rm -R -I ~/.wine -y --force;"
        "env WINEPREFIX=~/.wine WINEARCH=win32 winecfg;'"
        "ssh student@$i 'rm -R -I ~/.wine --force;"
        "env WINEPREFIX=~/.wine WINEARCH=win32 winecfg;"
        "winetricks --force -q dotnet472;"
        "winetricks -q d3dcompiler_47;"
        "winetricks -q vcrun2015;"
        "winetricks -q corefonts;"
        "reboot'"
        "done"
    )
    logging.info('Wine на ученических ПК установлен')
    print('Wine установлен')  

def KDE_fix():
    os.system(
        'hostname=$(kdialog --title="Настройка системы" --inputbox "Введите имя компьютера" $hostname;)'
        'echo $hostname'
        'ssh-add'     
        'do ssh root@$hostname "apt-get update --fix-missing && apt-get dist-upgrade -y && apt-get reinstall kde5-mini kde5-small gtk-theme-breeze-education sddm-theme-breeze kde5-display-manager-5-sddm plasma5-sddm-kcm sddm plasma5-khotkeys && reboot"'
        'done'
    )
def KDE_Lock():
    os.system(
        ''
    )

def main():
    """
    Главное меню
    """
    print('\n\n    ВНИМАНИЕ!\n\n'
          'Перед началом работы ознакомьтесь с инструкцией\n')
    if user == 'root':
        logging.info("Попытка запустить от рута")
        print("Данный скрипт не следует запускать от имени суперпользователя")
        exit_app()
    logging.info("Попытка создать папку /home/admin/teacher_control")
    os.system('mkdir -p /home/admin/teacher_control')
    logging.info("Успешно создана папка /home/admin/teacher_control")
    try:
        with open("/home/admin/teacher_control/hosts.txt", "r") as hosts:
            hosts.close()
        os.system('ln -s /home/admin/teacher_control/hosts.txt hosts.txt')
        logging.info("файл host найден и открыт")
    except IOError:
        with open("/home/admin/teacher_control/hosts.txt", "w") as hosts:
            hosts.close()
        os.system('ln -s /home/admin/teacher_control/hosts.txt hosts.txt')
        print(
            'Сгенерирован файл hosts.txt, '
            'перечислите в нём имена компьютеров построчно и запустите скрипт повторно.\n\n'
            '    ВАЖНО!\n\nДля М ОС имя компьютера должно оканчиваться на .local, пример: s-1111-2-kab3-4.local')
        logging.info("файл hosts не был найден, создан")
        exit_app()

    while True:
        print('\nВыберите действие:\n\n'
              '[1] - Включение УЗ Admin в полноценные администраторы (ВЫПОЛНЯТЬ В ПЕРВУЮ ОЧЕРЕДЬ!)\n'
              '[2] - настроить доступ по ssh для всех компьютеров из вашего файла hosts.txt\n'
              '[3] - создать сетевую папку share и копировать её ярлык на устройства учеников '
              '(требуется настроенный ssh)\n'
              '[4] - установить veyon на всех компьютерах в кабинете (занимает немного времени)\n'
              '[5] - включить Wake-On-Lan\n'
              '[6] - включить резолв имён пк для винды\n'
              '[7] - удалить UDS, mos-invent и mos-tele\n'
              '[8] - установить Wine (занимает много времени)\n'
              '[9] - ремонт сломаного окна авторизации по имени ПК (по ssh, нужно вести имя пк с припиской .local на конце) \n'
              '[10] - установка ограничений рабочего стола Student \n'
              '\n\n[0] - выход')
        print("Введите номер действия и нажмите Enter:")
        logging.info("Открыто главное меню")
        answer = int(input())
        logging.info(f"Введено {answer}")
        if answer == 1:
            sudo_admin()
        if answer == 2:
            setup_ssh()
        if answer == 3:
            test_ssh()
            network_folders()
        if answer == 4:
            test_ssh()
            install_veyon()
        if answer == 5:
            test_ssh()
            wol_on()
        if answer == 6:
            test_ssh()
            resolve_hostname()    
        if answer == 7:
            test_ssh()
            FuckYouCCO()
        if answer == 8:
            test_ssh()
            wine_install()
        if answer == 9:
            test_ssh()
            KDE_fix()
        if answer == 10:

        if answer == 0:
            exit_app()


if __name__ == "__main__":
    main()
