#!/bin/bash

SERVICE_NAME=nsb-agent
SERVICE_FOLDER=/usr/local/deployer/smartbackup
NUMBER_OF_PARAMETERS=""

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

function ReinstallCheck
{
    while
    local REINSTALLREPLY
    read -p "| Do you want to reinstall the agent? [Yes|No]" REINSTALLREPLY
    do
    case "$REINSTALLREPLY" in
        [yY][eE][sS] | [yY] )
            echo "Reinstalling agent"
            break
            ;;
        [nN][oO] | [nN] )
            echo "Aborting"
            exit 1
            ;;
        * )
            echo "Please answer [Yes|No]"
            ;;
    esac
    done
}


function Unpack
{
    # Clean previous versions of files
    rm -rf $SERVICE_FOLDER

    # Create folder
    mkdir -p $SERVICE_FOLDER
    cp deployer-smart-backup.tar $SERVICE_FOLDER

    # Change directory and unpack
    cd $SERVICE_FOLDER
    tar -xf deployer-smart-backup.tar
    chown -R root:root /usr/local/deployer/
    chmod +x ./nsb-agent
    chmod +x ./scripts/*
    chmod +x ./jq

    # Clean
    rm deployer-smart-backup.tar
}


function MySqlSettings
{
    while
    local MYSQLREPLY
    read -r -p "Do you want to configure MySQL consistency? [Yes|No] " MYSQLREPLY
    do
    case "$MYSQLREPLY" in
        [yY][eE][sS] | [yY] )
            MySqlInfo
            break
            ;;
        [nN][oO] | [nN] )
            break
            ;;
        * )
            echo "Please answer [Yes|No]"
            ;;
    esac
    done
}

function MySqlInfo
{
    echo "MySQL Configuration"
    echo "Provide your username, password and database information"

    read -p "| => Insert your MySQL Username: " username
    read -s -p "| => Insert your MySQL Password: " password

    while
    local ALLDBREPLY
    read -p "| Do you want to provide consistency for all MySQL DBs? [Yes|No]" ALLDBREPLY
    do
    case "$ALLDBREPLY" in
        [yY][eE][sS] | [yY] )
            echo "\"mysql\":{\"username\":\"$username\",\"password\":\"$password\",\"database_url\":\"localhost\"}" >> config_plugins.json
            chmod 600 config_plugins.json
            break
            ;;
        [nN][oO] | [nN] )
            read -p "| => Insert your MySQL DB Name: " database_name
            echo "\"mysql\":{\"username\":\"$username\",\"password\":\"$password\",\"database_url\":\"localhost\",\"database_name\":\"$database_name\"}" > config_plugins.json
            chmod 600 config_plugins.json
            break
            ;;
        * )
            echo "Please answer [Yes|No]"
            ;;
    esac
    done
}

function MySqlInstall
{
    echo "\"mysql\":{\"username\":\"admin\",\"password\":\"password1111\",\"database_url\":\"localhost\"}" >> config_plugins.json
    chmod 600 config_plugins.json
}


function MongoSettings
{
    while
    local MONGOREPLY
    read -r -p "Do you want to configure mongoDB consistency? [Yes|No] " MONGOREPLY
    do
    case "$MONGOREPLY" in
        [yY][eE][sS] | [yY] )
            MongoInfo
            break
            ;;
        [nN][oO] | [nN] )
            break
            ;;
        * )
            echo "Please answer [Yes|No]"
            ;;
    esac
    done
}


function MongoInfo
{
    echo "mongoDB Configuration"
    echo "Provide your admin username, password and database information"

    while
    local MONGOAUTH
    read -p "| Does mongoDB have authentication? [Yes|No]" MONGOAUTH
    do
    case "$MONGOAUTH" in
        [yY][eE][sS] | [yY] )
            read -p "| => Insert your mongoDB Username: " mongousername
            read -s -p "| => Insert your mongoDB Password: " mongopassword
            echo ""
            read -p "| => Insert your mongoDB Authentication Database: " mongoauthdb
            echo ""
            echo "\"mongo\":{\"username\":\"$mongousername\",\"password\":\"$mongopassword\",\"auth_db\":\"$mongoauthdb\",\"auth\":\"yes\"}" >> config_plugins.json
            chmod 600 config_plugins.json
            break
            ;;
        [nN][oO] | [nN] )
            echo "\"mongo\":{\"auth\":\"no\"}" >> config_plugins.json
            chmod 600 config_plugins.json
            break
            ;;
        * )
            echo "Please answer [Yes|No]"
            ;;
    esac
    done
}

function MongoInstall
{
    echo "\"mongo\":{\"username\":\"admin\",\"password\":\"deployer\",\"auth_db\":\"deployer\",\"auth\":\"yes\"}" >> config_plugins.json
    chmod 600 config_plugins.json
}



function ClientInfo
{
    if ! [[ $NUMBER_OF_PARAMETERS = 2 ]] ; then
            echo "Agent Registration"
            echo "Provide UUID and API-KEY given by the deployer Smart Backup portal"

            read -p "| => Insert the UUID: " uuid
            read -p "| => Insert the API-KEY: " apiKey
    fi

    echo "{\"client\":{\"uuid\":\"$uuid\",\"api_key\":\"$apiKey\"}}" > config.json

    #Join the two JSON and remove temporary files

    chmod 600 config.json
}


function CleanUp
{
    echo
    echo "        +----------------------------------------+"
    echo "        | deployer Smart Backup Agent Installed |"
    echo "        +----------------------------------------+"
    echo
}


function Install
{
    # Check if script is run as root
    if [[ $EUID -ne 0 ]]; then
            echo "This script must be run as root" 1>&2
            exit 1
    fi

    case "${INIT}" in
        'sysv')
            service $SERVICE_NAME stop
            ;;
        'upstart')
            initctl stop $SERVICE_NAME
            ;;
        'systemd')
            systemctl stop $SERVICE_NAME.service
            ;;
    esac

    Unpack
    . $SERVICE_FOLDER/scripts/init_helper.sh
    echo "{" > config_plugins.json
    MySqlInstall
    MongoInstall
    echo "}" >> config_plugins.json
    ClientInfo

    # Test run
    $SERVICE_FOLDER/nsb-agent-exec test_run 2>&1 >/dev/null
    ret=$?
    if [[ ${ret} -ne 0 ]]; then
        echo "Sorry it appears your system is not compatible with deployer Smart Backup Agent"
        echo "Installation aborted."
        exit 1
    fi

    ServiceEnable
    ServiceStart

    case "${INIT}" in
        'sysv')
            if grep unrecognized <(service nsb-agent status 2>&1) &>/dev/null ; then
                echo "Installation Failed" 1>&2
                exit 1
            else
                CleanUp
            fi
            ;;
        'upstart')
            if grep unknown <(initctl status $SERVICE_NAME 2>&1) &>/dev/null ; then
                echo "Installation Failed" 1>&2
                exit 1
            else
                CleanUp
            fi
            ;;
        'systemd')
            if grep not-found <(systemctl status $SERVICE_NAME.service 2>&1) &>/dev/null ; then
                echo "Installation Failed" 1>&2
                exit 1
            else
                CleanUp
            fi
            ;;
    esac

    # Start service at the end of install
    echo "Starting deployer Smart Backup Agent"
    ServiceStart
}


# ==================
#   StartUp Script
# ==================
# Detect init system
if [[ `/sbin/init --version` =~ upstart ]]; then
    echo "found upstart"
    INIT=upstart
elif [[ `systemctl` =~ -\.mount ]]; then
    echo "found systemd"
    INIT=systemd
elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then
    echo "found system V"
    INIT=sysv
else
    Unpack
    echo "sorry, we are not able to detect your init system (sysv, upstart or systemd)."
    echo "Please refer to your distribution documentation for manual installing a service with respawn,"
    echo "you will find all files unpacked in /usr/local/deployer/smartbackup with configuration"
    echo "files for all init systems."
    exit 1
fi

if [[ $# = 2 ]]  ; then
        uuid=$1
        apiKey=$2
        NUMBER_OF_PARAMETERS=$#
        echo "UUID: $uuid" 
        echo "API-KEY: $apiKey"
fi
        
Install





