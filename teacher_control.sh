#!/bin/sh
d=$(kdialog --radiolist "Выберите действие" 1 "Собрать работы" on 2 "Забрать одну работу" off 3 "Очистить всё" off 4 "Очистить одну машину" off 5 "Восстановить всё" off 6 "Восстановить одну машину" off)
#echo $d
cnthosts=$(cat /home/teacher/teacher_control/hosts.txt | wc -l)
maxprogress=2
if [ $d = 1 ] ; then
	maxprogress=$((cnthosts+1))
	dbusRef=$(kdialog --title="Работа с архивом" --progressbar "Инициализация" $maxprogress)
	qdbus $dbusRef Set "" value 0
	qdbus $dbusRef setLabelText "Собрать работы"
	dd=$(date +"%Y-%m-%d")
	h=$(kdialog --inputbox 'Введите название')
	c=0
	for i in $(cat /home/teacher/teacher_control/hosts.txt)
	do		
		c=$((c+1))
		qdbus $dbusRef Set "" value $c
		qdbus $dbusRef setLabelText "Собираем у "$i
		mkdir -p "/home/teacher/Рабочий стол/Работы/$dd/$h/$i" && ssh root@$i 'mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && chmod 777 /home/student/Рабочий\ стол/Сдать\ работы' && scp -r root@$i:'/home/student/Рабочий\ стол/Сдать\ работы/*' "/home/teacher/Рабочий стол/Работы/$dd/$h/$i"
	done
fi
if [ $d = 2 ] ; then
	dbusRef=`kdialog --title="Работа с архивом" --progressbar "Инициализация" 2`
	qdbus $dbusRef Set "" value 1
	qdbus $dbusRef setLabelText "Забрать одну работу"
	dd=$(date +"%Y-%m-%d")
	h=$(kdialog --combobox 'Выберите хостнейм\n' $(cat /home/teacher/teacher_control/hosts.txt))
	foldername=$(kdialog --inputbox 'Введите название')
	mkdir -p "/home/teacher/Рабочий стол/Работы/$dd/$foldername/$h" && ssh root@$h 'mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && chmod 777 /home/student/Рабочий\ стол/Сдать\ работы' && scp -r root@$h:'/home/student/Рабочий\ стол/Сдать\ работы/*' "/home/teacher/Рабочий стол/Работы/$dd/$foldername/$h"
fi
if [ $d = 3 ] ; then
	maxprogress=$((cnthosts+1))
	dbusRef=$(kdialog --title="Работа с архивом" --progressbar "Инициализация" $maxprogress)
	qdbus $dbusRef Set "" value 0
	qdbus $dbusRef setLabelText "Очистить все папки"
	c=0
	for i in $(cat /home/teacher/teacher_control/hosts.txt)
	do
		c=$((c+1))
		qdbus $dbusRef Set "" value $c
		qdbus $dbusRef setLabelText "Очищаем "$i
		ssh root@$i 'rm -rf /home/student/Рабочий\ стол/Сдать\ работы/*'
	done
fi
if [ $d = 4 ] ; then
	dbusRef=`kdialog --title="Работа с архивом" --progressbar "Инициализация" 2`
	qdbus $dbusRef Set "" value 1
	qdbus $dbusRef setLabelText "Очистить одну папку"
	h=$(kdialog --combobox 'Выберите хостнейм\n' $(cat /home/teacher/teacher_control/hosts.txt))
	ssh root@$h 'rm -rf /home/student/Рабочий\ стол/Сдать\ работы/*';
fi
if [ $d = 5 ] ; then
	maxprogress=$((cnthosts+1))
	dbusRef=$(kdialog --title="Работа с архивом" --progressbar "Инициализация" $maxprogress)
	qdbus $dbusRef Set "" value 0
	qdbus $dbusRef setLabelText "Восстановить всё"
	c=0
	for i in $(cat /home/teacher/teacher_control/hosts.txt)
	do
		c=$((c+1))
		qdbus $dbusRef Set "" value $c
		qdbus $dbusRef setLabelText "Восстанавливаем "$i
		ssh root@$i "pkill -u student; cd /home && if [[ ! -f /home/student.tar.gz ]]; then echo 'На '$i' нет архива student!'; else echo 'sleep 5 && rm -rf student && tar xfz student.tar.gz && mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && chmod 777 /home/student/Рабочий\ стол/Сдать\ работы && reboot' | at now && echo $i' восстановлен'; fi"
	done
fi
if [ $d = 6 ] ; then
	dbusRef=`kdialog --title="Работа с архивом" --progressbar "Инициализация" 2`
	qdbus $dbusRef Set "" value 1
	qdbus $dbusRef setLabelText "Восстановить одну машину"
	h=$(kdialog --combobox 'Выберите хостнейм\n' $(cat /home/teacher/teacher_control/hosts.txt))
	ssh root@$h "pkill -u student; cd /home && if [[ ! -f /home/student.tar.gz ]]; then echo 'На '$h' нет архива student!'; else echo 'sleep 5 && rm -rf student && tar xfz student.tar.gz && mkdir -p /home/student/Рабочий\ стол/Сдать\ работы && chmod 777 /home/student/Рабочий\ стол/Сдать\ работы && reboot' | at now; fi"
fi
qdbus $dbusRef Set "" value $maxprogress
qdbus $dbusRef setLabelText "Завершено"
sleep 1
qdbus $dbusRef close


