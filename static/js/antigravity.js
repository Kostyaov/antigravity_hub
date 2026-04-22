/**
 * Antigravity Hub JS Engine
 * Handles dynamic tab execution and auto-theming of HTML elements (creating HUD Dropdowns).
 */

class AntigravityEngine {
    constructor() {
        this.initTabs();
        this.autoTheme();
        this.initGlobalDropdownListeners();
    }

    initTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                
                const targetId = btn.dataset.target;
                const targetContent = document.getElementById(targetId);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });
    }

    autoTheme() {
        // Auto convert all <select> elements that have class="ag-select" or just general selects
        // If a plugin developer puts <select class="ag-select"> it becomes a HUD dropdown automatically.
        const selects = document.querySelectorAll('select.ag-select');
        selects.forEach(select => {
            if (select.dataset.hudInitialized) return; // already processed
            
            const dropdownId = select.id ? `hud-${select.id}` : `hud-${Math.random().toString(36).substr(2, 9)}`;
            select.dataset.hudInitialized = "true";
            select.style.display = 'none'; // hide original select
            
            const hudWrapper = document.createElement('div');
            hudWrapper.className = 'hud-dropdown';
            hudWrapper.id = dropdownId;
            hudWrapper.dataset.originalSelectId = select.id;
            
            // Get current selected text
            const selectedOption = select.options[select.selectedIndex];
            const triggerText = selectedOption ? selectedOption.text : "Select...";
            hudWrapper.dataset.value = selectedOption ? selectedOption.value : "";
            
            const trigger = document.createElement('div');
            trigger.className = 'hud-dropdown-trigger';
            trigger.innerText = triggerText;
            
            const optionsWrapper = document.createElement('div');
            optionsWrapper.className = 'hud-dropdown-options';
            
            Array.from(select.options).forEach((opt, index) => {
                const optDiv = document.createElement('div');
                optDiv.className = 'hud-dropdown-option' + (opt.selected ? ' selected' : '');
                optDiv.dataset.value = opt.value;
                optDiv.innerText = opt.text;
                optionsWrapper.appendChild(optDiv);
            });
            
            hudWrapper.appendChild(trigger);
            hudWrapper.appendChild(optionsWrapper);
            select.parentNode.insertBefore(hudWrapper, select.nextSibling);
        });
        
        // Auto-style plain buttons if they don't have btn class but are form buttons
        const basicBtns = document.querySelectorAll('button:not(.btn):not(.tab-btn):not(.theme-btn):not(.modal-close)');
        basicBtns.forEach(btn => {
            if(btn.dataset.themeIgnored) return;
            btn.classList.add('btn');
        });

        // Initialize HUD logic for all HUD components present (even those manually created)
        this.initHudDropdowns();
    }

    initHudDropdowns() {
        document.querySelectorAll('.hud-dropdown').forEach(dropdown => {
            if (dropdown.dataset.eventsBound) return;
            dropdown.dataset.eventsBound = "true";

            const trigger = dropdown.querySelector('.hud-dropdown-trigger');
            
            trigger.onclick = (e) => {
                e.stopPropagation();
                const isOpen = dropdown.classList.contains('open');
                this.closeAllDropdowns();
                if (!isOpen) dropdown.classList.add('open');
            };

            dropdown.addEventListener('click', (e) => {
                if (e.target.classList.contains('hud-dropdown-option')) {
                    const val = e.target.dataset.value;
                    const text = e.target.innerText;
                    
                    dropdown.dataset.value = val;
                    trigger.innerText = text;
                    
                    dropdown.querySelectorAll('.hud-dropdown-option').forEach(opt => opt.classList.remove('selected'));
                    e.target.classList.add('selected');
                    dropdown.classList.remove('open');
                    
                    // If this HUD dropdown was auto-generated from a <select>, update the original select
                    const origId = dropdown.dataset.originalSelectId;
                    if (origId) {
                        const origSelect = document.getElementById(origId);
                        if (origSelect) {
                            origSelect.value = val;
                            origSelect.dispatchEvent(new Event('change')); // Trigger event for bindings
                        }
                    }
                    
                    // Trigger global event for custom manually bound HUDs
                    const event = new CustomEvent('hud-change', { detail: { id: dropdown.id, value: val }});
                    dropdown.dispatchEvent(event);
                }
            });
        });
    }

    closeAllDropdowns() {
        document.querySelectorAll('.hud-dropdown').forEach(d => d.classList.remove('open'));
    }

    initGlobalDropdownListeners() {
        document.addEventListener('click', () => this.closeAllDropdowns());
    }
}

class AntigravitySettings {
    constructor() {
        this.modal = document.getElementById('settingsModal');
        this.btnOpen = document.getElementById('settingsBtn');
        this.btnClose = document.getElementById('closeSettingsBtn');
        this.themeBtns = document.querySelectorAll('.theme-btn');
        this.langSelect = document.getElementById('langSelect');
        
        this.currentTheme = localStorage.getItem('ag_theme') || 'theme-amber';
        this.currentLang = localStorage.getItem('ag_lang') || 'uk';
        
        this.translations = {
            'uk': {
                'app_title': 'Antigravity Hub',
                'settings_title': 'НАЛАШТУВАННЯ',
                'theme_label': 'Колірна Тема (HUD)',
                'lang_label': 'Мова Інтерфейсу'
            },
            'en': {
                'app_title': 'Antigravity Hub',
                'settings_title': 'SETTINGS',
                'theme_label': 'Color Theme (HUD)',
                'lang_label': 'Interface Language'
            }
        };

        this.init();
    }

    init() {
        console.log("[*] Antigravity Settings Initializing...");
        // Modal toggling
        if (this.btnOpen) {
            this.btnOpen.addEventListener('click', () => {
                console.log("[*] Opening Settings Modal");
                this.modal.classList.add('active');
            });
        }
        
        if (this.btnClose) {
            this.btnClose.addEventListener('click', () => {
                console.log("[*] Closing Settings Modal");
                this.modal.classList.remove('active');
            });
        }
        
        // Close on overlay click
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) this.modal.classList.remove('active');
            });
        }

        // Theme initialization
        this.setTheme(this.currentTheme);
        this.themeBtns.forEach(btn => {
            btn.addEventListener('click', () => this.setTheme(btn.dataset.theme));
        });

        // Language initialization
        if (this.langSelect) {
            this.langSelect.value = this.currentLang;
            
            // Listen to original select change
            this.langSelect.addEventListener('change', (e) => {
                this.setLanguage(e.target.value);
            });
            // Listen to HUD change
            const hudId = `hud-${this.langSelect.id}`;
            document.addEventListener('hud-change', (e) => {
                if(e.detail.id === hudId) this.setLanguage(e.detail.value);
            });
        }
        this.setLanguage(this.currentLang);
    }

    setTheme(themeClass) {
        this.currentTheme = themeClass;
        localStorage.setItem('ag_theme', themeClass);
        
        // Remove old themes
        document.body.classList.remove('theme-amber', 'theme-cyan', 'theme-emerald');
        document.body.classList.add(themeClass);

        // Update active button state
        this.themeBtns.forEach(btn => {
            if (btn.dataset.theme === themeClass) btn.classList.add('active');
            else btn.classList.remove('active');
        });
    }

    setLanguage(langCode) {
        if (!this.translations[langCode]) return;
        this.currentLang = langCode;
        localStorage.setItem('ag_lang', langCode);
        
        const dict = this.translations[langCode];
        
        // Translate all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            if (dict[key]) {
                el.innerText = dict[key];
            }
        });
    }
}

// Global initialization when the DOM is fully loaded or replaced
document.addEventListener('DOMContentLoaded', () => {
    window.agEngine = new AntigravityEngine();
    window.agSettings = new AntigravitySettings();
});
