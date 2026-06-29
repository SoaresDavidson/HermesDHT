import os
import secrets
import string
import hashlib
import base64
import re

def load_env():
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^([^=\s]+)\s*=\s*(.*)$", line)
                if match:
                    env_vars[match.group(1).strip()] = match.group(2).strip()
    return env_vars

def main():
    conf_dir = "./qbittorrent/config/qBittorrent"
    conf_file = f"{conf_dir}/qBittorrent.conf"
    
    # Garante que a pasta de configuração exista
    os.makedirs(conf_dir, exist_ok=True)

    # 1. Carrega variáveis existentes ou gera novas chaves do qBittorrent
    env = load_env()
    qbit_pass = env.get("QBITTORRENT_PASS")

    if not qbit_pass:
        alphabet = string.ascii_letters + string.digits
        qbit_pass = "".join(secrets.choice(alphabet) for _ in range(16))

    # 2. Hashing PBKDF2-HMAC-SHA512 para o qBittorrent.conf
    iterations = 100000
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha512", qbit_pass.encode(), salt, iterations)
    encoded_salt = base64.b64encode(salt).decode()
    encoded_hash = base64.b64encode(dk).decode()
    password_pbkdf2 = f'@ByteArray({encoded_salt}:{encoded_hash})'

    # 3. Lê ou inicializa o qBittorrent.conf
    lines = []
    if os.path.exists(conf_file):
        with open(conf_file, "r") as f:
            lines = f.readlines()
    else:
        lines = [
            "[Application]\n",
            "FileLogger\\Enabled=true\n",
            "FileLogger\\Path=/config/qBittorrent/logs\n",
            "\n",
            "[LegalNotice]\n",
            "Accepted=true\n",
            "\n",
            "[Preferences]\n",
            "Downloads\\SavePath=/downloads/\n",
            "WebUI\\Address=*\n",
            "WebUI\\ServerDomains=*\n"
        ]

    # 4. Atualiza as configurações no qBittorrent.conf
    new_lines = []
    in_preferences = False
    in_legal_notice = False
    updated_keys = {
        "WebUI\\Password_PBKDF2": False,
        "WebUI\\AuthSubnetWhitelist": False,
        "WebUI\\AuthSubnetWhitelistEnabled": False,
        "WebUI\\LocalHostAuth": False
    }
    updated_legal = {
        "Accepted": False
    }

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            if in_preferences:
                for k, updated in updated_keys.items():
                    if not updated:
                        if k == "WebUI\\Password_PBKDF2":
                            new_lines.append(f'{k}="{password_pbkdf2}"\n')
                        elif k == "WebUI\\AuthSubnetWhitelist":
                            new_lines.append(f'{k}=172.16.0.0/12\n')
                        elif k == "WebUI\\AuthSubnetWhitelistEnabled":
                            new_lines.append(f'{k}=true\n')
                        elif k == "WebUI\\LocalHostAuth":
                            new_lines.append(f'{k}=false\n')
                        updated_keys[k] = True
            if in_legal_notice:
                if not updated_legal["Accepted"]:
                    new_lines.append("Accepted=true\n")
                    updated_legal["Accepted"] = True
                    
            in_preferences = (stripped == "[Preferences]")
            in_legal_notice = (stripped == "[LegalNotice]")
            new_lines.append(line)
            continue

        if in_preferences:
            key_match = re.match(r"^([^=\s]+)\s*=\s*(.*)$", stripped)
            if key_match:
                key = key_match.group(1)
                if key in updated_keys:
                    if key == "WebUI\\Password_PBKDF2":
                        new_lines.append(f'{key}="{password_pbkdf2}"\n')
                    elif key == "WebUI\\AuthSubnetWhitelist":
                        new_lines.append(f'{key}=172.16.0.0/12\n')
                    elif key == "WebUI\\AuthSubnetWhitelistEnabled":
                        new_lines.append(f'{key}=true\n')
                    elif key == "WebUI\\LocalHostAuth":
                        new_lines.append(f'{key}=false\n')
                    updated_keys[key] = True
                    continue

        if in_legal_notice:
            key_match = re.match(r"^([^=\s]+)\s*=\s*(.*)$", stripped)
            if key_match:
                key = key_match.group(1)
                if key == "Accepted":
                    new_lines.append("Accepted=true\n")
                    updated_legal["Accepted"] = True
                    continue

        new_lines.append(line)

    # Insere chaves se Preferences/Legal for a última seção do arquivo
    if in_preferences:
        for k, updated in updated_keys.items():
            if not updated:
                if k == "WebUI\\Password_PBKDF2":
                    new_lines.append(f'{k}="{password_pbkdf2}"\n')
                elif k == "WebUI\\AuthSubnetWhitelist":
                    new_lines.append(f'{k}=172.16.0.0/12\n')
                elif k == "WebUI\\AuthSubnetWhitelistEnabled":
                    new_lines.append(f'{k}=true\n')
                elif k == "WebUI\\LocalHostAuth":
                    new_lines.append(f'{k}=false\n')
                updated_keys[k] = True
    if in_legal_notice:
        if not updated_legal["Accepted"]:
            new_lines.append("Accepted=true\n")
            updated_legal["Accepted"] = True

    # Se as seções não existirem no arquivo original, cria-as no final
    if not any(k for k in updated_keys.values()):
        new_lines.append("\n[Preferences]\n")
        new_lines.append(f'WebUI\\Password_PBKDF2="{password_pbkdf2}"\n')
        new_lines.append('WebUI\\AuthSubnetWhitelist=172.16.0.0/12\n')
        new_lines.append('WebUI\\AuthSubnetWhitelistEnabled=true\n')
        new_lines.append('WebUI\\LocalHostAuth=false\n')
    if not updated_legal["Accepted"]:
        new_lines.append("\n[LegalNotice]\n")
        new_lines.append("Accepted=true\n")

    with open(conf_file, "w") as f:
        f.writelines(new_lines)

    # 5. Atualiza o arquivo .env com as novas credenciais
    env_lines = []
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            env_lines = f.readlines()

    new_env_lines = []
    updated_env = {
        "QBITTORRENT_PASS": False
    }

    for line in env_lines:
        stripped = line.strip()
        key_match = re.match(r"^([^=\s]+)\s*=\s*(.*)$", stripped)
        if key_match:
            key = key_match.group(1)
            if key in updated_env:
                if key == "QBITTORRENT_PASS":
                    new_env_lines.append(f"QBITTORRENT_PASS={qbit_pass}\n")
                updated_env[key] = True
                continue
        new_env_lines.append(line)

    for k, updated in updated_env.items():
        if not updated:
            new_env_lines.append(f"{k}={qbit_pass}\n")

    with open(".env", "w") as f:
        f.writelines(new_env_lines)

    # Output para leitura dos scripts shell
    print(f"PASSWORD:{qbit_pass}")

if __name__ == "__main__":
    main()
