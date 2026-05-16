#!/bin/bash

# Spinner function
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

echo "=============================================="
echo "Installing EnderPull..."
echo "=============================================="

echo -n "[ 🛠️ ] Initializing isolated environment... "
(python3 -m venv venv || python -m venv venv) >/dev/null 2>&1 &
spinner $!
echo "[ ✔️ ]"

echo -n "[ 📥 ] Installing dependencies and registering EnderPull... "
(source venv/bin/activate && pip install -e .) >/dev/null 2>&1 &
spinner $!
echo "[ ✔️ ]"

echo "[ 🪄 ] Generating launch script..."
cat << 'EOF' > launch.sh
#!/bin/bash
venv/bin/python3 -m enderpull "$@"
EOF
chmod +x launch.sh

echo "[ 🧹 ] Performing deep cleanup..."
rm -f requirements.txt README.md .gitignore install.bat

echo "=============================================="
echo "[ ✔️ ] Installation Complete!"
echo "=============================================="
sleep 2

./launch.sh --help

rm -- "$0"
