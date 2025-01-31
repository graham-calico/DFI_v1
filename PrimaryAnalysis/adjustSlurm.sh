#!/bin/bash

# increase sub limits for slurm
echo "increasing SLURM array max size"
cp /usr/local/etc/slurm/slurm.conf fullNewSlurm.conf
chmod u+w fullNewSlurm.conf
cat confAdds.txt >> fullNewSlurm.conf
sudo mv fullNewSlurm.conf /usr/local/etc/slurm/slurm.conf
# do the restart
sudo systemctl restart slurmctld

echo "Done."

