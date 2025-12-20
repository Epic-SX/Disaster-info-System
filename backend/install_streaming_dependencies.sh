#!/bin/bash
# Installation script for YouTube Live streaming dependencies

echo "========================================="
echo "Installing YouTube Live Streaming Dependencies"
echo "========================================="

# Update package list
echo "Updating package list..."
sudo apt-get update

# Install FFmpeg
echo "Installing FFmpeg..."
sudo apt-get install -y ffmpeg

# Install Xvfb (X Virtual Framebuffer)
echo "Installing Xvfb..."
sudo apt-get install -y xvfb

# Install additional dependencies
echo "Installing additional dependencies..."
sudo apt-get install -y \
    x11-xserver-utils \
    xfonts-base \
    xfonts-75dpi \
    xfonts-100dpi

# Verify installations
echo ""
echo "========================================="
echo "Verifying installations..."
echo "========================================="

if command -v ffmpeg &> /dev/null; then
    echo "✓ FFmpeg installed: $(ffmpeg -version | head -n1)"
else
    echo "✗ FFmpeg installation failed"
fi

if command -v Xvfb &> /dev/null; then
    echo "✓ Xvfb installed: $(Xvfb -help 2>&1 | head -n1)"
else
    echo "✗ Xvfb installation failed"
fi

echo ""
echo "========================================="
echo "Installation complete!"
echo "========================================="
echo "You can now use the YouTube Live streaming feature."
echo ""
echo "To start streaming:"
echo "1. Go to the YouTube Live tab in the dashboard"
echo "2. Enter your YouTube stream key"
echo "3. Click 'Start Streaming'"

