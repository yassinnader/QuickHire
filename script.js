// Improved, modern, and "senior dev"-quality handler for #careerForm (QuickHire AI)
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('careerForm');
    if (!form) return;

    // ==== Toast Notification System ====
    function showToast(message, type = 'info') {
        let toast = document.getElementById('qh-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'qh-toast';
            toast.setAttribute('role', 'alert');
            Object.assign(toast.style, {
                position: 'fixed', bottom: '32px', right: '32px', 
                padding: '14px 22px', borderRadius: '7px',
                background: '#222', color: '#fff',
                fontSize: '1rem', zIndex: 9999, minWidth: '200px',
                boxShadow: '0 6px 32px rgba(0,0,0,0.20)',
                transition: 'opacity 0.35s', opacity: '0', pointerEvents: 'none'
            });
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.background = (
            type === 'success' ? '#10b981' : 
            type === 'error' ? '#ef4444' :
            type === 'warning' ? '#f59e0b' : '#222'
        );
        toast.style.opacity = '1';
        toast.style.pointerEvents = 'auto';
        clearTimeout(showToast._timeout);
        showToast._timeout = setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.pointerEvents = 'none';
        }, 2600);
    }

    // ==== Download Blob as File (uses a11y best-practices) ====
    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 150);
    }

    // ==== Form Submission Handler ====
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Accessibility: Announce progress
        let statusLive = document.getElementById('qh-status');
        if (!statusLive) {
            statusLive = document.createElement('div');
            statusLive.id = 'qh-status';
            statusLive.setAttribute('role', 'status');
            statusLive.className = 'sr-only';
            document.body.appendChild(statusLive);
        }
        statusLive.textContent = 'Generating documents...';

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnHTML = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

        // Get credits & plan
        let credits = parseInt(localStorage.getItem('quickhire_credits') || '1', 10);
        const userPlan = localStorage.getItem('quickhire_plan') || 'free';
        if (userPlan !== 'premium' && credits <= 0) {
            showToast('No credits left. Please invite friends or upgrade.', 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHTML;
            return;
        }

        // Gather form data (robust extraction)
        const getVal = id => (document.getElementById(id)?.value || '').trim();
        const formData = {
            current_position: getVal('currentPosition'),
            years_experience: getVal('yearsExperience'),
            education: getVal('education'),
            skills: Array.from(document.querySelectorAll('#skills-tags .skill-tag')).map(tag => tag.firstChild.textContent.trim()),
            experience: getVal('experience'),
            target_position: getVal('targetPosition'),
            achievements: getVal('achievements'),
            projects: getVal('projects'),
            industry: getVal('industry'),
            tone: getVal('tone'),
            job_description: getVal('jobDescription'),
        };

        // Validate required fields
        const requiredFields = ['current_position', 'years_experience', 'target_position', 'industry'];
        for (const key of requiredFields) {
            if (!formData[key]) {
                showToast('Please fill out all required fields.', 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHTML;
                return;
            }
        }

        // Show progress bar (demo animation)
        const progressBar = document.getElementById('progress-container');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        if (progressBar && progressFill && progressText) {
            progressBar.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = 'Generating your documents...';
        }

        try {
            // ========== Generate Resume ==========
            const resumeRes = await fetch('http://localhost:8000/generate-resume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (!resumeRes.ok) throw new Error('Failed to generate resume.');

            const resumeBlob = await resumeRes.blob();
            downloadBlob(resumeBlob, 'QuickHire_Resume.pdf');

            // ========== Generate Cover Letter ==========
            const coverLetterRes = await fetch('http://localhost:8000/generate-cover-letter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (!coverLetterRes.ok) throw new Error('Failed to generate cover letter.');

            const coverLetterBlob = await coverLetterRes.blob();
            downloadBlob(coverLetterBlob, 'QuickHire_Cover_Letter.pdf');

            // ========== Update credits & UI ==========
            if (userPlan !== 'premium') {
                credits -= 1;
                localStorage.setItem('quickhire_credits', credits);
            }
            document.getElementById('credit-count').textContent = userPlan === 'premium' ? '∞' : credits;

            showToast('Your Resume & Cover Letter are ready!', 'success');
            statusLive.textContent = 'Generation complete.';

            // Animate progress bar to completion
            if (progressBar && progressFill && progressText) {
                progressFill.style.width = '100%';
                progressText.textContent = 'Done!';
                setTimeout(() => { progressBar.style.display = 'none'; }, 1200);
            }
        } catch (error) {
            console.error(error);
            showToast('❌ Error: ' + (error.message || error), 'error');
            statusLive.textContent = 'Error occurred.';
            if (progressBar) progressBar.style.display = 'none';
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHTML;
        }
    });

    // ==== Plan & Credits UI Update ====
    function updatePlanUI() {
        const userPlan = localStorage.getItem('quickhire_plan') || 'free';
        const planLabel = document.getElementById('plan-label');
        if (planLabel) planLabel.textContent = userPlan.charAt(0).toUpperCase() + userPlan.slice(1);
        const creditCountEl = document.getElementById('credit-count');
        if (creditCountEl) {
            let credits = parseInt(localStorage.getItem('quickhire_credits') || '1', 10);
            creditCountEl.textContent = userPlan === 'premium' ? '∞' : credits;
        }
    }
    updatePlanUI();

    // ==== Tab Switch (Keyboard & Mouse) ====
    document.querySelectorAll('.form-tab').forEach(tabBtn => {
        tabBtn.addEventListener('click', function () {
            const tab = this.dataset.tab || 
                (this.textContent.toLowerCase().includes('basic') ? 'basic' :
                this.textContent.toLowerCase().includes('experience') ? 'experience' : 'preferences');
            switchTab(tab);
        });
        tabBtn.addEventListener('keydown', function(e) {
            if (e.key === "Enter" || e.key === " ") this.click();
        });
    });

    function switchTab(tab) {
        ['basic', 'experience', 'preferences'].forEach(t => {
            const content = document.getElementById(`${t}-tab`);
            if (content) content.style.display = (t === tab) ? '' : 'none';
            const tabBtn = document.querySelector(`.form-tab[data-tab="${t}"]`);
            if (tabBtn) tabBtn.classList.toggle('active', t === tab);
        });
    }

    // ==== Skills Input Tagging ====
    const skillsInput = document.getElementById('skills');
    const skillsTags = document.getElementById('skills-tags');
    function addSkill(event) {
        if (event.key === 'Enter' && skillsInput.value.trim()) {
            event.preventDefault();
            const value = skillsInput.value.trim();
            if ([...skillsTags.children].some(tag => tag.firstChild.textContent.trim() === value)) return;
            const tag = document.createElement('span');
            tag.className = 'skill-tag';
            tag.innerHTML = `<span>${value}</span> <i class="fas fa-times remove" tabindex="0" aria-label="Remove skill"></i>`;
            tag.querySelector('.remove').onclick = () => { tag.remove(); };
            tag.querySelector('.remove').onkeydown = e => { if (e.key === "Enter" || e.key === " ") tag.remove(); };
            skillsTags.appendChild(tag);
            skillsInput.value = '';
        }
    }
    skillsInput?.addEventListener('keypress', addSkill);

    // ==== Document Type Selection ====
    document.querySelectorAll('.document-type').forEach(typeDiv => {
        typeDiv.addEventListener('click', function () {
            this.classList.toggle('selected');
            this.setAttribute('aria-pressed', this.classList.contains('selected'));
        });
        typeDiv.tabIndex = 0;
        typeDiv.setAttribute('role', 'button');
        typeDiv.setAttribute('aria-pressed', typeDiv.classList.contains('selected'));
        typeDiv.addEventListener('keydown', function(e){
            if (e.key === "Enter" || e.key === " ") this.click();
        });
    });

    // ==== Modal Action Shortcuts ====
    window.showSignup = () => showToast('Show Signup Modal (demo)');
    window.showLogin = () => showToast('Show Login Modal (demo)');
    window.showUpgrade = () => showToast('Show Upgrade Modal (demo)');
    window.showReferral = () => showToast('Show Referral Modal (demo)');
    window.showHistory = () => showToast('Show History Modal (demo)');

    // ==== Progress Bar on Generation (for demo) ====
    const progressBar = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    if (progressBar && progressFill && progressText) {
        form.addEventListener('submit', function () {
            progressBar.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.innerText = 'Generating your documents...';
            let progress = 0;
            const interval = setInterval(() => {
                progress += 10;
                progressFill.style.width = progress + '%';
                if (progress >= 100) {
                    clearInterval(interval);
                    progressText.innerText = 'Done!';
                }
            }, 150);
        });
    }

    // ==== Keyboard Shortcuts ====
    document.addEventListener('keydown', function(e){
        if (e.altKey && e.key.toLowerCase() === 't') document.getElementById('theme-toggle')?.click();
        if (e.key === 'Escape') { document.querySelector('.modal[style*="block"]')?.style.setProperty('display','none'); }
    });
});