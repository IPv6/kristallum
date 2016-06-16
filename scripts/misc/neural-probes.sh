# https://github.com/jcjohnson/neural-style
cd ~/Documents/Zzz/neurpaint/neural-style-master/
~/torch/install/bin/th neural_style.lua -style_image ../style.jpg -content_image ../target.jpg -output_image ../result -init image -content_weight 100 -style_weight 200 -normalize_gradients -gpu -1 -num_iterations 1000
#-init image -content_weight 100 -style_weight 1500 -normalize_gradients
