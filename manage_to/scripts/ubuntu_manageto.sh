#!/bin/bash -xe
apt update
apt upgrade -y
# python3 available on Ubuntu AMIs
# SSM Agent is available on 20.04, 18.04, and 16.04 LTS 64-bit AMIs with an identifier of 20180627 or later.
# check if SSM Agent is running
sudo snap services amazon-ssm-agent