# Init script collection for non-systemd distro

## Slackware

Create a group podman and add your user to the podman group.

    sudo groupadd -r podman
    sudo usermod -a -G podman <YOUR_USER>

Copy the file rc.podman in /etc/rc.d/ then make it executable and start the service.



    sudo cp rc.podman /etc/rc.d/
    sudo chmod +x /etc/rc.d/rc.podman
    sudo /etc/rc.d/rc.podman start

Logout and login into your system or alternatively login into a new shell.

    sudo -iu <YOUR_USER>
    id <YOUR_USER>

