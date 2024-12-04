#!/bin/sh

if [ -e /usr/sbin/tailscaled ]
then
    echo "Tailscale already installed, exiting."
    exit 1
fi

read -p "Enter Tailscale auth key: " authkey

wget https://pkgs.tailscale.com/stable/tailscale_1.70.0_arm.tgz -O /tmp/tailscale_1.70.0_arm.tgz

echo "4b7f1ff722221bd538bac679f2227ab59a9760720724c6d3f0570939bc4454c4  /tmp/tailscale_1.70.0_arm.tgz" | sha256sum -c

tar xvzf /tmp/tailscale_1.70.0_arm.tgz -C /tmp

mv /tmp/tailscale_1.70.0_arm/tailscaled /usr/sbin/tailscaled
mv /tmp/tailscale_1.70.0_arm/tailscale /usr/sbin/tailscale

cat << EOF >> /etc/sysupgrade.conf
/etc/init.d/tailscale
/etc/rc.d/*tailscale
/etc/tailscale/
/lib/upgrade/keep.d/tailscale
/usr/sbin/tailscale
/usr/sbin/tailscaled
EOF

cat << EOF > /etc/init.d/tailscaled
#!/bin/sh /etc/rc.common

# Copyright 2020 Google LLC.
# SPDX-License-Identifier: Apache-2.0

USE_PROCD=1
START=80

start_service() {
  /usr/sbin/tailscaled --cleanup

  procd_open_instance
  procd_set_param command /usr/sbin/tailscaled

  # Set the port to listen on for incoming VPN packets.
  # Remote nodes will automatically be informed about the new port number,
  # but you might want to configure this in order to set external firewall
  # settings.
  procd_append_param command --port 41641

  # OpenWRT /var is a symlink to /tmp, so write persistent state elsewhere.
  procd_append_param command --state /etc/tailscale/tailscaled.state

  procd_set_param respawn
  procd_set_param stdout 1
  procd_set_param stderr 1

  procd_close_instance
}

stop_service() {
  /usr/sbin/tailscaled --cleanup
}
EOF

chmod +x /etc/init.d/tailscaled

mkdir -pv /etc/tailscale/

/etc/init.d/tailscaled enable
/etc/init.d/tailscaled start

tailscale up --auth-key=$authkey
