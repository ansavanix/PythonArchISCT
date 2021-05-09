#Initialize installation string
installString = "#!/bin/bash\n"
usingKernelParameters = 0
kernelParameters = ""
#Function to simplify asking the user for input
def ask(prompt, options):
	output = input("Enter " + prompt + " " + options+ ": ")
	return output

def command(command):
	global installString
	installString += command + "\n"

def archroot(command):
	global installString
	installString += "arch-chroot /mnt " + command + "\n"


def kernelParameter(parameter):
	global kernelParameters
	global usingKernelParameters
	usingKernelParameters = 1
	kernelParameters += " " + parameter
	
	
def installPackages(packages):
	global installString
	installString += "arch-chroot /mnt pacman -S --noconfirm " + packages + "\n"

print("Starting script creation process...")

#Ask user for configuration details for installation script
#Plans:
#Add full disk encryption option
#Add options to allow user to configure disks manually
#Add more security/hardening options
rootDisk = ask("root disk","Example: sda")
bootMethod = ask("boot method","uefi/bios")
kernel = ask("kernel","regular/lts/hardened/zen")
firmware = ask("if proprietary firmware is needed","y/n")
hostname = ask("hostname/computer name","Example: ArchComputer")
microcode = ask("if microcode updates are need","y/n")
if (microcode == "y"):
	processorManufacturer = ask("amd or intel" , "amd/intel")
firewall = ask("if firewall is needed","y/n")
user = "y"
username = ask("Username?", "Example: archuser")
apparmor = ask("whether to install and enable apparmor", "y/n")
if (apparmor == "y"):
 	firejail = ask("whether to install firejail", "y/n")
awesome = ask("whether to install awesome wm and start on login", "y/n")
if (awesome == "y"):
	firefox = ask("whether to install firefox", "y/n")
	vim = ask("whether to install vim and some plugins", "y/n")
kvmhost = ask("if you are using this machine as a virtualization host using qemu/kvm", "y/n")
print("Beginning creation of Arch Linux installation script.")



#Create partitions depending on boot method
if (bootMethod == "uefi"):
	tabletype = "gpt"
	firstPartition = "fat32 1 512"
else:
	tabletype = "msdos"
	firstPartition = "primary 1 100%FREE"
command("timedatectl set-ntp true")
command("parted /dev/" + rootDisk + " mklabel " + tabletype)
command("parted /dev/" + rootDisk + " mkpart " + firstPartition)

#Format partitions based on boot method
if (bootMethod == "uefi"):
	command("parted /dev/" + rootDisk + " mkpart ext4 512 100%FREE")
	command("mkfs.ext4 /dev/" + rootDisk + "2")
	command("mkfs.fat -F32 /dev/" + rootDisk + "1")
	command("mount /dev/" + rootDisk + "2 /mnt")
	command("mkdir /mnt/boot")
	command("mkdir /mnt/boot/efi")
	command("mount /dev/" + rootDisk + "1 /mnt/boot/efi")
else:
	command("mkfs.ext4 /dev/" + rootDisk + "1")
	command("mount /dev/" + rootDisk + "1 /mnt")

#Decide what kernel to use
if (kernel == "lts"):
	kernelString = "linux-lts"
elif (kernel == "zen"):
	kernelString = "linux-zen"
elif (kernel == "hardened"):
	kernelString = "linux-hardened"
else:
	kernelString = "linux"

#Decide whether or not to install linux-firmware package
if (firmware == "n"):
	firmwareString = ""
else:
	firmwareString = " linux-firmware"

#Setup the base system
command("pacstrap /mnt base " + kernelString + firmwareString + " nano")
command("genfstab -U /mnt >> /mnt/etc/fstab")
archroot("timedatectl set-timezone America/Los_Angeles")
archroot("ln -sf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime")
command("echo en_US.UTF-8 UTF-8 > /mnt/etc/locale.gen")
command("echo LANG=en_US.UTF-8 > /mnt/etc/locale.conf")
archroot("locale-gen")
command("echo " + hostname + " > /mnt/etc/hostname")
archroot("hostnamectl set-hostname " + hostname)
archroot("passwd --lock root")

#Install microcode if selected
if (microcode == "y"):
	if (processorManufacturer == "intel"):
		installPackages("intel-ucode")
	else:
		installPackages("amd-ucode")

#Install and enable ufw if firewall is selected
if (firewall == "y"):
	installPackages("ufw")
	 archroot("systemctl enable ufw")
	 archroot("ufw enable")

#Create the user if selected
if (user == "y"):
	installPackages("doas")
	archroot("useradd -m " + username)
	command("echo 'permit " + username + " as root' > /mnt/etc/doas.conf")
	archroot("passwd " + username)

#Install and enable apparmor
if (apparmor == "y"):
	 installPackages("apparmor")
	 archroot("systemctl enable apparmor")
	 kernelParameter("lsm=lockdown,yama,apparmor,bpf")

#Setup the bootloader(grub)
if (bootMethod == "uefi"):
	installPackages("grub efibootmgr")
	archroot("grub-install /dev/" + rootDisk)
else:
	installPackages("grub")
	archroot("grub-install /dev/" + rootDisk)

#Add kernel parameters before making grub config file
if (usingKernelParameters == 1):
	 command("sed -i 's/loglevel=3 quiet/loglevel=3 quiet" + kernelParameters +"/' /mnt/etc/default/grub")
	 archroot("grub-mkconfig -o /boot/grub/grub.cfg")

#Setup networking with connman(connection manager)
installPackages("connman")
archroot("systemctl enable connman")

#Install awesome firefox, and vim if wanted
if (awesome == "y"):
	 installPackages("awesome xorg-xinit xorg")
	if (firefox == "y"):
		installPackages("firefox pulseaudio pavucontrol firefox-ublock-origin firefox-extension-https-everywhere")
	command("echo 'awesome' > /mnt/home/" + username + "/.xinitrc")
	command("echo 'startx - --keeptty &> ~/.xorg.log' >> /mnt/home/" + username + "/.bash_profile")
	if (vim == "y"):
		installPackages("vim vim-jedi vim-gitgutter vim-vital")

#Install packages to allow machine to be a virtualization host utilizing qemu, kvm, and libvirt
if (kvmhost == "y"):
	installPackages("libvirt qemu openbsd-netcat ebtables dnsmasq bridge-utils")
	archroot("systemctl enable libvirtd")

#Install and configure firejail
if (firejail == "y"):
	installPackages("firejail")
	archroot("firecfg")

#Alert the user that the installation has finished
command("echo INSTALLATION FINISHED!")

#Write installString to a file
scriptFile = open("ArchInstallScript.bash", "w")
scriptFile.write(installString)
scriptFile.close()

#Alert user script has been written
print("Script has been written to file.")
