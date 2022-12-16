#!/bin/sh

if [[ $(whoami) == 'root' ]]
then
    chpasswd <<<'root:password'
    useradd admin && gpasswd -a admin wheel && chpasswd <<<'admin:password'
    useradd teacher && chpasswd <<<'teacher:password'
    useradd student && chpasswd <<<'student:password'
    chpasswd <<<'root:password'
    deluser -f -r <<<'user'
    echo "Done"
    if id student &>/dev/null
    then
        sed -i'.bak' -E -e 's,^Session.+,Session=plasma,' -e 's,^User.+,User=student,' /etc/X11/sddm/sddm.conf
    fi
    reboot
else
    echo 'Требуется запускать от рута'
fi
