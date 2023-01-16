import subprocess


def sendMessage(message):
    subprocess.Popen(['notify-send', message])
    return


def sendMessageIcon(message, icon):
    subprocess.Popen(['notify-send', '-i', icon, message])
    return


def sendMessageTitle(message, title):
    subprocess.Popen(['notify-send', title, message])
    return


def msg(message, title, icon):
    subprocess.Popen(['notify-send', title, '-i', icon, message])
    return
