# overall data for the project
# REQUIRES: the input video must be found in this bucket
input_mov_project = 'FILL-IN-gcp-project-name-for-bucket'
input_mov_bucket = 'FILL-IN-gcp-bucket-name'
input_mov_folder = 'FILL-IN-folder-path'

# the order in which analysis will be run
aInfoL = []

outD_wheel = {}
outD_wheel['name'] = 'wheel'
outD_wheel['out_project'] = 'FILL-IN-gcp-project-name-for-bucket'
outD_wheel['out_bucket'] = 'FILL-IN-gcp-bucket-name'
outD_wheel['out_folder'] = 'FILL-IN-folder-path'
aInfoL.append(outD_wheel)

# just the position, for the obj detector
outD_box = {}
outD_box['name'] = 'box'
outD_box['out_project'] = 'FILL-IN-gcp-project-name-for-bucket'
outD_box['out_bucket'] = 'FILL-IN-gcp-bucket-name'
outD_box['out_folder'] = 'FILL-IN-folder-path'
aInfoL.append(outD_box)

# includes hair, body weight, bedding
outD_minute = {}
outD_minute['name'] = 'minute'
outD_minute['out_project'] = 'FILL-IN-gcp-project-name-for-bucket'
outD_minute['out_bucket'] = 'FILL-IN-gcp-bucket-name'
outD_minute['out_folder'] = 'FILL-IN-folder-path'
aInfoL.append(outD_minute)
