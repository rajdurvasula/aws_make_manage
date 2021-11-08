import os
import sys
import stat
from datetime import date, datetime
import json
import boto3
import botocore
import paramiko
import requests

mfrom_priv_key_file = "kyndryl_rd_tok.pem"
ssh_priv_key_file = "ssh_key"
ssh_pub_key_file = "ssh_key.pub"

def datetime_serialize(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s is not serializable" % type(obj))

def create_user(remote_host, sudo_user, remote_user, allow_sudo):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=remote_host,username=sudo_user,key_filename=mfrom_priv_key_file)
    print('Connected to remote_host: %s' % remote_host)
    add_user = "sudo useradd "+remote_user
    stdin,stdout,stderr = ssh_client.exec_command(add_user)
    if (stdout.channel.recv_exit_status() == 0):
        print('User %s created' % remote_user)
        if allow_sudo:
            configure_sudo(remote_host, sudo_user, remote_user)
    else:
        print(stderr.readlines())

def configure_sudo(remote_host, sudo_user, remote_user):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=remote_host,username=sudo_user,key_filename=mfrom_priv_key_file)
    print('Connected to remote_host: %s' % remote_host)
    sudo_entry = remote_user+"        ALL=(ALL)       NOPASSWD: ALL"
    stdin,stdout,stderr = ssh_client.exec_command('sudo bash -c \"echo \\"'+sudo_entry+'\\" >> /etc/sudoers\"')
    if (stdout.channel.recv_exit_status() == 0):
        print('User %s added to sudoers' % remote_user)
    else:
        print(stderr.readlines())

def add_authorized_key(remote_host, sudo_user, remote_user):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=remote_host,username=sudo_user,key_filename=mfrom_priv_key_file)
    print('Connected to remote_host: %s' % remote_host)
    content = read_file(ssh_pub_key_file)
    stdin,stdout,stderr = ssh_client.exec_command("sudo getent passwd  | grep %s | cut -d: -f6" % remote_user)
    if (stdout.channel.recv_exit_status() == 0):
        user_home = stdout.readlines()[0].replace('\n','')
        stdin,stdout,stderr = ssh_client.exec_command("sudo mkdir -p %s/.ssh" % user_home)
        if (stdout.channel.recv_exit_status() == 0):
            stdin,stdout,stderr = ssh_client.exec_command('sudo bash -c \"echo \\"%s\\" > %s/.ssh/authorized_keys\"' % (content, user_home))
            if (stdout.channel.recv_exit_status() == 0):
                stdin,stdout,stderr = ssh_client.exec_command("sudo chown -R %s:%s %s" % (remote_user, remote_user, user_home))
                print('Public Key added to authorized_keys.')
            else:
                print("Unable to create %s/.ssh/authorized_keys" % user_home)
                print(stderr.readlines())
        else:
            print("Unable to create %s/.ssh on remote host" % user_home)
            print(stderr.readlines())
    else:
        print("User %s not found" % remote_user)
        print(stderr.readlines())


def get_keys(sudo_user_key_name, priv_key_name, pub_key_name):
    aws_region = get_region()
    sm_client = boto3.client('secretsmanager', region_name=aws_region)
    try:
        response =sm_client.get_secret_value(SecretId=sudo_user_key_name)
        sudo_key_content = response['SecretString']
        with open(mfrom_priv_key_file, 'w') as sudoer_key_file:
            sudoer_key_file.write(sudo_key_content)
        sudoer_key_file.close()
        os.chmod(mfrom_priv_key_file, stat.S_IRUSR)
        print('Sudo user key downloaded. File = %s' % mfrom_priv_key_file)

        response = sm_client.get_secret_value(SecretId=priv_key_name)
        priv_key_content = response['SecretString']
        with open(ssh_priv_key_file, 'w') as priv_key_file:
            priv_key_file.write(priv_key_content)
        priv_key_file.close()
        os.chmod(ssh_priv_key_file, stat.S_IRUSR)
        print('Private key downloaded. File = %s' % ssh_priv_key_file)

        response = sm_client.get_secret_value(SecretId=pub_key_name)
        pub_key_content = response['SecretString'].replace('\n','')
        with open(ssh_pub_key_file, 'w') as pub_key_file:
            pub_key_file.write(pub_key_content)
        pub_key_file.close()
        os.chmod(ssh_pub_key_file, stat.S_IRUSR)
        print('Public key downloaded. File = %s' % ssh_pub_key_file)
    except botocore.exceptions.ClientError as ce:
        if ce.response['Error']['Code'] == '404':
            print('Object does not exist')
        else:
            raise

def read_file(file_name):
    with open(file_name, 'r') as my_file:
        file_content = my_file.readlines()
    return file_content[0]

def install_ssm_agent(remote_host, sudo_user):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=remote_host,username=sudo_user,key_filename=mfrom_priv_key_file)
    print('Connected to remote_host: %s' % remote_host)
    command = "cat /etc/os-release | grep '^ID=' | cut -d'=' -f2 | sed -r 's#\"##g'"
    stdin,stdout,stderr = ssh_client.exec_command(command)
    if (stdout.channel.recv_exit_status() == 0):
        os_name = stdout.readlines()[0].strip()
        if os_name == "sles":
            install_ssm_agent_sles(remote_host, sudo_user)
        elif os_name == "rhel":
            install_ssm_agent_rhel(remote_host, sudo_user)

def install_ssm_agent_sles(remote_host, sudo_user):
    # get AWS region from Manage_from instance
    aws_region = get_region()
    command = "wget https://s3.%s.amazonaws.com/amazon-ssm-%s/latest/linux_amd64/amazon-ssm-agent.rpm" % (aws_region, aws_region)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=remote_host,username=sudo_user,key_filename=mfrom_priv_key_file)
    print('Connected to remote_host: %s' % remote_host)
    stdin,stdout,stderr = ssh_client.exec_command(command)
    if (stdout.channel.recv_exit_status() == 0):
        command = "sudo rpm --install amazon-ssm-agent.rpm"
        stdin,stdout,stderr = ssh_client.exec_command(command)
        if (stdout.channel.recv_exit_status() == 0):
            print('SSM Agent is installed')
            command = "sudo systemctl enable amazon-ssm-agent"
            stdin,stdout,stderr = ssh_client.exec_command(command)
            if (stdout.channel.recv_exit_status() == 0):
                print('SSM Agent is enabled')
            command = "sudo systemctl start amazon-ssm-agent"
            stdin,stdout,stderr = ssh_client.exec_command(command)
            if (stdout.channel.recv_exit_status() == 0):
                print('SSM Agent is started')
        else:
            print('SSM Agent installation failed !')
            print(stderr.readlines())

def install_ssm_agent_rhel(remote_host, sudo_user):
    # get AWS region from Manage_from instance
    aws_region = get_region()
    command = "sudo yum install -y https://s3.%s.amazonaws.com/amazon-ssm-%s/latest/linux_amd64/amazon-ssm-agent.rpm" % (aws_region, aws_region)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=remote_host,username=sudo_user,key_filename=mfrom_priv_key_file)
    print('Connected to remote_host: %s' % remote_host)
    stdin,stdout,stderr = ssh_client.exec_command(command)
    if (stdout.channel.recv_exit_status() == 0):
        print('SSM Agent is installed')
        command = "sudo systemctl enable amazon-ssm-agent"
        stdin,stdout,stderr = ssh_client.exec_command(command)
    else:
        print('SSM Agent installation failed !')
        print(stderr.readlines())

def get_region():
    get_response = requests.get(url='http://169.254.169.254/latest/meta-data/placement/region')
    return get_response.text

def usage():
    print('usage: makemanage_linux.py priv_key_name pub_key_name remote_host sudo_user sudo_user_key remote_user sudoer|no_sudoer')
    sys.exit(0)

def main():
    if (len(sys.argv) != 8):
        usage()
    priv_key_name = sys.argv[1]
    pub_key_name = sys.argv[2]
    remote_host = sys.argv[3]
    sudo_user = sys.argv[4]
    sudo_user_key_name = sys.argv[5]
    remote_user = sys.argv[6]
    allow_sudo = "sudoer" == sys.argv[7]
    get_keys(sudo_user_key_name, priv_key_name, pub_key_name)
    create_user(remote_host, sudo_user, remote_user, allow_sudo)
    add_authorized_key(remote_host, sudo_user, remote_user)
    install_ssm_agent(remote_host, sudo_user)

if __name__ == '__main__':
    main()
