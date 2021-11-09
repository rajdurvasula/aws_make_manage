#!/bin/bash -xe
# pre-reqs for domain join
sudo yum -y install sssd realmd krb5-workstation samba-common-tools
touch /etc/dhcp/dhclient.conf
# IP address of DNS server
echo "supersede domain-name-servers 10.0.0.18;" >> /etc/dhcp/dhclient.conf
echo "PEERDNS=yes" >> /etc/sysconfig/network-scripts/ifcfg-eth0
# reboot
# domain join - interactive
realm join -v -U rddeladmin@mspad.net mspad.net --install=/
# allow password authentication
sed -i -e "s~PasswordAuthentication no~PasswordAuthentication yes~g" /etc/ssh/sshd_config
# Not SUDOER
# reboot
# domain join - non-interactive
# launch script
realm join mspad.net -U <ad_user>
# expect script
#!/bin/expect -f
spawn ./launch_domain_join.sh
expect "Password for <ad_user>: "
send -- "<password>"
send -- "\r"
expect eof
# wait for sssd service status = running
# then, reboot
