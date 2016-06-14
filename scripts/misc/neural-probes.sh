# https://github.com/jcjohnson/neural-style
cd ~/Documents/Zzz/neurpaint/neural-style-master/
~/torch/install/bin/th neural_style.lua -style_image ../style.jpg -content_image ../target.jpg
#-content_weight 100 -style_weight 1500 -init image -normalize_gradients
#-gpu -1
