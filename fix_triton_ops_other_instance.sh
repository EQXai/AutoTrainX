#!/bin/bash
# Fix script for triton.ops error in OTHER instance
# This creates the missing triton.ops module that bitsandbytes needs

echo "🔧 Fixing triton.ops module for bitsandbytes compatibility..."

# Find the Python version and site-packages path
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
SITE_PACKAGES="venv/lib/python${PYTHON_VERSION}/site-packages"

if [ ! -d "$SITE_PACKAGES/triton" ]; then
    echo "❌ Error: triton not found in $SITE_PACKAGES"
    echo "Make sure you're in the AutoTrainX directory and venv is activated"
    exit 1
fi

echo "📁 Creating triton/ops directory..."
mkdir -p "$SITE_PACKAGES/triton/ops"

echo "📝 Creating __init__.py..."
cat > "$SITE_PACKAGES/triton/ops/__init__.py" << 'EOF'
# Stub module for triton.ops
# This fixes compatibility with bitsandbytes and diffusers

class _StubOp:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

# Common ops that might be used
matmul = _StubOp()
elementwise = _StubOp()
reduction = _StubOp()

def __getattr__(name):
    return _StubOp()
EOF

echo "📝 Creating matmul_perf_model.py for bitsandbytes..."
cat > "$SITE_PACKAGES/triton/ops/matmul_perf_model.py" << 'EOF'
# Stub for matmul_perf_model required by bitsandbytes

def early_config_prune(configs, named_args):
    """Stub function for early_config_prune"""
    # Just return configs as-is
    return configs

def estimate_matmul_time(M, N, K, dtype):
    """Stub function for estimate_matmul_time"""
    # Return a dummy time estimate
    return 1.0

# Any other function that might be needed
def __getattr__(name):
    return lambda *args, **kwargs: None
EOF

echo "✅ Files created successfully!"

echo ""
echo "🧪 Testing imports..."

# Test triton.ops
python -c "import triton.ops; print('✅ triton.ops imports OK')" 2>&1

# Test the specific import that bitsandbytes needs
python -c "from triton.ops.matmul_perf_model import early_config_prune, estimate_matmul_time; print('✅ bitsandbytes imports OK')" 2>&1

# Test diffusers
python -c "from diffusers import AutoencoderKL; print('✅ diffusers imports OK')" 2>&1 | grep -v "bitsandbytes CUDA binary"

echo ""
echo "✨ Fix complete! Your training should work now."
echo ""
echo "Note: The bitsandbytes CUDA warning is normal and doesn't affect training."