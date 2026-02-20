方案 1（最简单，继续用 pigpio_if2）

源码装 pigpio v79：

git clone https://github.com/joan2937/pigpio.git
cd pigpio
make
sudo make install
sudo ldconfig


然后：

sudo pigpiod -t 1