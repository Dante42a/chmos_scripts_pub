#!/bin/sh
myhostname=$(hostname)
myhostname=$(kdialog --title="Настройка системы" --inputbox "Введите имя компьютера" $myhostname)
echo $myhostname
pkexec bash -c 'rm -f /etc/machine-id && rm -f /var/lib/dbus/machine-id && dbus-uuidgen --ensure && systemd-machine-id-setup && hostnamectl hostname '$myhostname' && reboot'
