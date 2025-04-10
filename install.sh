#!/usr/bin/env bash

set -e
set -u
set -o pipefail

APP_NAME="ImageConverter"
SCRIPT_NAME="image_converter_gui.py"
PREFERRED_ICON_NAME="icon.png"
FALLBACK_ICON_NAME="icon.ico"
INSTALL_BASE_DIR="${HOME}/.local/share"
INSTALL_DIR="${INSTALL_BASE_DIR}/${APP_NAME}"
VENV_DIR="${INSTALL_DIR}/venv"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER_SCRIPT_NAME="image-converter"
LAUNCHER_SCRIPT_PATH="${BIN_DIR}/${LAUNCHER_SCRIPT_NAME}"
DESKTOP_ENTRY_DIR="${HOME}/.local/share/applications"
DESKTOP_ENTRY_NAME="${APP_NAME}.desktop"
DESKTOP_ENTRY_PATH="${DESKTOP_ENTRY_DIR}/${DESKTOP_ENTRY_NAME}"
ICON_INSTALL_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"


err() {
  echo "[!] Error: $*" >&2
  exit 1
}

msg() {
  echo "[*] $*"
}

uninstall() {
    msg "Starting uninstallation of ${APP_NAME}..."

    if [ -f "${DESKTOP_ENTRY_PATH}" ]; then
        msg "Removing desktop entry: ${DESKTOP_ENTRY_PATH}"
        rm -f "${DESKTOP_ENTRY_PATH}"
    fi

    local THEMED_ICON_PATH="${ICON_INSTALL_DIR}/${APP_NAME}.png"
    if [ -f "${THEMED_ICON_PATH}" ]; then
         msg "Removing themed icon: ${THEMED_ICON_PATH}"
         rm -f "${THEMED_ICON_PATH}"
    fi

    if command -v update-desktop-database &> /dev/null; then
        msg "Updating desktop database..."
        update-desktop-database "${DESKTOP_ENTRY_DIR}" &> /dev/null || msg "  (Optional) Failed to update desktop database."
    fi
    if command -v gtk-update-icon-cache &> /dev/null; then
        msg "Updating icon cache..."
        gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" &> /dev/null || msg "  (Optional) Failed to update icon cache."
    fi


    if [ -f "${LAUNCHER_SCRIPT_PATH}" ]; then
        msg "Removing launcher script: ${LAUNCHER_SCRIPT_PATH}"
        rm -f "${LAUNCHER_SCRIPT_PATH}"
    fi

    if [ -d "${INSTALL_DIR}" ]; then
        msg "Removing installation directory: ${INSTALL_DIR}"
        rm -rf "${INSTALL_DIR}"
    fi

    msg "${APP_NAME} uninstalled successfully."
    exit 0
}

install() {
    msg "Starting installation of ${APP_NAME}..."

    msg "Checking prerequisites..."
    if ! command -v python3 &> /dev/null; then err "python3 not found"; fi
    msg "  [+] Python 3 found: $(command -v python3)"
    if ! python3 -c "import venv" &> /dev/null; then err "python3-venv module not found"; fi
    msg "  [+] Python 3 venv module found."

    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
    msg "  [*] Looking for source files in: ${SCRIPT_DIR}"

    if [ ! -f "${SCRIPT_DIR}/${SCRIPT_NAME}" ]; then err "Script not found: ${SCRIPT_DIR}/${SCRIPT_NAME}"; fi
    msg "  [+] Application script found."

    local SOURCE_ICON_PATH=""
    local FINAL_ICON_NAME=""
    if [ -f "${SCRIPT_DIR}/${PREFERRED_ICON_NAME}" ]; then
        msg "  [+] Using preferred icon: ${PREFERRED_ICON_NAME}"
        SOURCE_ICON_PATH="${SCRIPT_DIR}/${PREFERRED_ICON_NAME}"
        FINAL_ICON_NAME="${PREFERRED_ICON_NAME}" 
    elif [ -f "${SCRIPT_DIR}/${FALLBACK_ICON_NAME}" ]; then
        msg "  [*] Using fallback icon: ${FALLBACK_ICON_NAME} (PNG format is recommended)"
        SOURCE_ICON_PATH="${SCRIPT_DIR}/${FALLBACK_ICON_NAME}"
        FINAL_ICON_NAME="${FALLBACK_ICON_NAME}"
    else
        msg "  [!] Warning: No icon file found (icon.png or icon.ico). Installing without icon."
    fi

    msg "Creating directories..."
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${BIN_DIR}"
    mkdir -p "${DESKTOP_ENTRY_DIR}"
    mkdir -p "${ICON_INSTALL_DIR}"
    msg "  [+] Directories created."

    msg "Creating Python virtual environment..."
    python3 -m venv "${VENV_DIR}" || err "Failed to create venv."
    msg "  [+] Virtual environment created."

    msg "Installing dependencies..."
    "${VENV_DIR}/bin/pip" install --upgrade pip &> /dev/null
    "${VENV_DIR}/bin/pip" install PyQt6 Pillow --no-cache-dir || err "Failed to install dependencies."
    msg "  [+] Dependencies installed."

    msg "Copying application files..."
    cp "${SCRIPT_DIR}/${SCRIPT_NAME}" "${INSTALL_DIR}/" || err "Failed to copy script."
    if [ -n "${SOURCE_ICON_PATH}" ]; then
        cp "${SOURCE_ICON_PATH}" "${INSTALL_DIR}/${FINAL_ICON_NAME}" || err "Failed to copy icon to app dir."

        if [ "${FINAL_ICON_NAME}" == "${PREFERRED_ICON_NAME}" ]; then
             cp "${SOURCE_ICON_PATH}" "${ICON_INSTALL_DIR}/${APP_NAME}.png" || err "Failed to copy icon to theme dir."
             msg "  [*] Copied icon to theme dir: ${ICON_INSTALL_DIR}/${APP_NAME}.png"
        fi
    fi
    msg "  [+] Files copied."

    msg "Creating launcher script..."
    tee "${LAUNCHER_SCRIPT_PATH}" > /dev/null << EOF
#!/usr/bin/env bash
cd "\${INSTALL_DIR}" # Change to app dir before running
exec "\${VENV_DIR}/bin/python" "\${INSTALL_DIR}/\${SCRIPT_NAME}" "\$@"
EOF
    chmod +x "${LAUNCHER_SCRIPT_PATH}" || err "Failed to make launcher executable."
    msg "  [+] Launcher script created."

    msg "Creating desktop entry..."

    local DESKTOP_ENTRY_ICON_VALUE="${APP_NAME}" 

    if [ "${FINAL_ICON_NAME}" != "${PREFERRED_ICON_NAME}" ] || [ -z "${FINAL_ICON_NAME}" ]; then
         DESKTOP_ENTRY_ICON_VALUE="${INSTALL_DIR}/${FINAL_ICON_NAME}" 
         if [ -z "${FINAL_ICON_NAME}" ]; then DESKTOP_ENTRY_ICON_VALUE=""; fi 
         msg "  [*] Using absolute icon path in desktop entry: ${DESKTOP_ENTRY_ICON_VALUE}"
    else
         msg "  [*] Using themed icon name in desktop entry: ${DESKTOP_ENTRY_ICON_VALUE}"
    fi


    local EXEC_COMMAND="env QT_QPA_PLATFORM=xcb ${VENV_DIR}/bin/python ${INSTALL_DIR}/${SCRIPT_NAME}"

    tee "${DESKTOP_ENTRY_PATH}" > /dev/null << EOF
[Desktop Entry]
Version=1.0
Name=${APP_NAME}
Comment=Convert images to WebP with options
Exec=${EXEC_COMMAND}
Path=${INSTALL_DIR}
Icon=${DESKTOP_ENTRY_ICON_VALUE}
Terminal=false
Type=Application
Categories=Utility;Graphics;
EOF
    chmod 644 "${DESKTOP_ENTRY_PATH}" || msg "  [!] Warning: Could not set permissions on desktop entry."
    msg "  [+] Desktop entry created."


    msg "Updating caches (may take a moment)..."
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "${DESKTOP_ENTRY_DIR}" &> /dev/null || msg "  (Optional) Failed to update desktop database."
    else
        msg "  [*] 'update-desktop-database' not found. Skipping."
    fi
    if command -v gtk-update-icon-cache &> /dev/null; then
        mkdir -p "${HOME}/.local/share/icons/hicolor"
        gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" &> /dev/null || msg "  (Optional) Failed to update icon cache."
    else
        msg "  [*] 'gtk-update-icon-cache' not found. Skipping."
    fi
    msg "  [+] Caches updated (attempted)."


    msg "--------------------------------------------------"
    msg "${APP_NAME} installation completed successfully!"
    msg "You can now run the application by:"
    msg "  1. Typing '${LAUNCHER_SCRIPT_NAME}' in your terminal."
    msg "  2. Finding '${APP_NAME}' in your desktop application menu (may need logout/login)."
    msg "To uninstall, run this script again with: ./install.sh --uninstall"
    msg "--------------------------------------------------"
}

if [ "$#" -gt 0 ] && [ "$1" == "--uninstall" ]; then
    uninstall
else
    if [ -d "${INSTALL_DIR}" ]; then
        msg "Existing installation found at ${INSTALL_DIR}. Reinstalling..."
    fi
    install
fi

exit 0
