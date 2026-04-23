// Password match validation
const registerForm = document.getElementById('registerForm');
if (registerForm) {
  const pw  = document.getElementById('password');
  const cpw = document.getElementById('confirmPassword');
  const err = document.getElementById('matchError');
  cpw.addEventListener('input', () => {
    err.style.display = (cpw.value && cpw.value !== pw.value) ? 'block' : 'none';
  });
  registerForm.addEventListener('submit', e => {
    if (pw.value !== cpw.value) { e.preventDefault(); err.style.display = 'block'; cpw.focus(); }
  });
}

// Image preview
const imgInput = document.getElementById('imageInput');
if (imgInput) {
  imgInput.addEventListener('change', function () {
    const prev = document.getElementById('imgPreview');
    const img  = document.getElementById('previewImg');
    if (this.files && this.files[0]) {
      const reader = new FileReader();
      reader.onload = e => { img.src = e.target.result; prev.style.display = 'block'; };
      reader.readAsDataURL(this.files[0]);
    }
  });
}

// Auto-hide flash alerts
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert').forEach(a => {
    setTimeout(() => {
      a.style.transition = 'opacity .4s';
      a.style.opacity = '0';
      setTimeout(() => a.remove(), 400);
    }, 4500);
  });
});
