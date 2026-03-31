// Password match validation
const registerForm = document.getElementById('registerForm');
if (registerForm) {
  const pw = document.getElementById('password');
  const cpw = document.getElementById('confirmPassword');
  const err = document.getElementById('matchError');
  cpw.addEventListener('input', () => {
    err.style.display = (cpw.value && cpw.value !== pw.value) ? 'block' : 'none';
  });
  registerForm.addEventListener('submit', e => {
    if (pw.value !== cpw.value) { e.preventDefault(); err.style.display = 'block'; cpw.focus(); }
  });
}

// Image preview on vehicle form
const imageInput = document.getElementById('imageInput');
if (imageInput) {
  imageInput.addEventListener('change', function () {
    const preview = document.getElementById('imgPreview');
    const img = document.getElementById('previewImg');
    if (this.files && this.files[0]) {
      const reader = new FileReader();
      reader.onload = e => { img.src = e.target.result; preview.style.display = 'block'; };
      reader.readAsDataURL(this.files[0]);
    }
  });
}

// Auto-hide flash alerts after 4
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 4000);
  });
});
