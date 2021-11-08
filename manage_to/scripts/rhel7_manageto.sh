#!/bin/bash -xe
setup_python() {
  echo "alias python=/usr/bin/python3" >> /etc/bashrc
  alias python=/usr/bin/python3
}

yum -y update
yum -y install git
if [ -f /usr/bin/python3 ]; then
  setup_python
else
  yum -y install python3 python3-devel
  setup_python
fi
sudo yum install -y https://s3.region.amazonaws.com/amazon-ssm-region/latest/linux_amd64/amazon-ssm-agent.rpm
systemctl enable amazon-ssm-agent