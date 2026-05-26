#!/bin/bash

# Define Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
RESET='\033[0m'

# Spinner function
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [ ${CYAN}WORKING${RESET} ] %c  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b"
    done
    printf "                    \b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b"
}

clear

echo -e "${CYAN}${BOLD}==============================================${RESET}"
echo -e "${CYAN}${BOLD}          [ ENDERPULL MOD MANAGER ]           ${RESET}"
echo -e "${CYAN}${BOLD}==============================================${RESET}"
echo

echo -n -e "[ ${CYAN}WORKING${RESET} ] 🛠️  Creating isolated virtual environment... "
(python3 -m venv venv || python -m venv venv) >/dev/null 2>&1 &
spinner $!
echo -e "\r[ ${GREEN}SUCCESS${RESET} ] 🛠️  Creating isolated virtual environment... "

echo -n -e "[ ${CYAN}WORKING${RESET} ] 📥  Downloading dependencies and caching files... "
(source venv/bin/activate && pip install -e .) >/dev/null 2>&1 &
spinner $!
echo -e "\r[ ${GREEN}SUCCESS${RESET} ] 📥  Downloading dependencies and caching files... "

rm -f requirements.txt README.md .gitignore install.bat launch.bat

sleep 1
clear

echo -e "${GREEN}${BOLD}[ SUCCESS ]${RESET} 🎉 EnderPull Installed Successfully!"
echo "--------------------------------------------------"
echo -e "${YELLOW}Transitioning to your interactive modding terminal...${RESET}"
sleep 3

chmod +x launch.sh
exec ./launch.sh
