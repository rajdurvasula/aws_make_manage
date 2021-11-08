#!/bin/bash

setup_python() {
  echo "alias python=/usr/bin/python3" >> /etc/bashrc
  alias python=/usr/bin/python3
}

yum -y update
yum -y install git
python=`which python3`
if [ "${python}" == "/usr/bin/python3" ]; then
  setup_python
else
  yum -y install python3 python3-devel
  setup_python
fi
alias python=/usr/bin/python3
python -m pip install --upgrade --user pip paramiko boto3
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
echo "PATH=\$PATH:/usr/local/bin" >> /etc/bashrc
echo "export PATH" >> /etc/bashrc
source /etc/bashrc
