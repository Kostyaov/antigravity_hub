/**
 * RSS Reader Core Logic (Vanilla JS Translation)
 */
class RSSReader {
    constructor() {
        console.log("[MyRSS] Initializing...");
        window.rssApp = this; // Attach early
        this.feeds = JSON.parse(localStorage.getItem('antigravity_rss_feeds')) || [
            { id: '1', title: 'The Verge', url: 'https://www.theverge.com/rss/index.xml', icon: 'news' },
            { id: '2', title: 'Hacker News', url: 'https://news.ycombinator.com/rss', icon: 'code' }
        ];
        this.activeFeedId = 'all';
        this.viewMode = 'grid';
        
        // Wait a tiny bit to ensure all modules are loaded in the DOM
        setTimeout(() => this.init(), 100);
    }

    init() {
        console.log("[MyRSS] Running Init...");
        try {
            this.renderFeeds();
            this.loadArticles();
            this.bindEvents();
            console.log("[MyRSS] Initialization Complete.");
        } catch (e) {
            console.error("[MyRSS] ERROR during initialization:", e);
        }
    }

    save() {
        localStorage.setItem('antigravity_rss_feeds', JSON.stringify(this.feeds));
    }

    // --- DOM Elements ---
    get elements() {
        const get = (id) => {
            const el = document.getElementById(id);
            if (!el) console.warn(`[MyRSS] Element not found: ${id}`);
            return el;
        };

        return {
            feedList: get('rss-feed-list'),
            articleContainer: get('rss-articles'),
            loadingOverlay: get('rss-loader'),
            addModal: get('rss-modal'),
            feedTitle: get('rss-view-title'),
            addBtn: get('rss-add-btn'),
            saveFeedBtn: get('rss-save-feed'),
            feedUrlInput: get('rss-url-input'),
            exportBtn: get('rss-export-btn'),
            importBtn: document.getElementById('rss-import-btn'),
            importInput: document.getElementById('rss-import-input')
        };
    }

    bindEvents() {
        const el = this.elements;
        console.log("[MyRSS] Binding events...");

        if (el.addBtn) {
            el.addBtn.onclick = () => {
                console.log("[MyRSS] Add button clicked");
                el.addModal.style.display = 'flex';
            };
        }

        if (el.saveFeedBtn) {
            el.saveFeedBtn.onclick = () => {
                console.log("[MyRSS] Save Feed clicked");
                this.handleAddFeed();
            };
        }

        if (el.exportBtn) el.exportBtn.onclick = () => this.handleExport();
        if (el.importBtn) el.importBtn.onclick = () => el.importInput.click();
        if (el.importInput) el.importInput.onchange = (e) => this.handleImport(e);

        // Close modal on click outside
        window.addEventListener('click', (event) => {
            if (el.addModal && event.target == el.addModal) {
                el.addModal.style.display = "none";
            }
        });

        // View mode switchers
        document.querySelectorAll('[data-rss-view]').forEach(btn => {
            btn.onclick = () => {
                console.log("[MyRSS] View mode changed to:", btn.dataset.rssView);
                this.viewMode = btn.dataset.rssView;
                this.loadArticles();
            };
        });
    }

    async fetchFeed(url) {
        try {
            const res = await fetch(`https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(url)}`);
            const data = await res.json();
            if (data.status === 'ok') {
                return data.items.map(item => ({
                    ...item,
                    feedTitle: data.feed.title,
                    feedUrl: url,
                    pubDate: new Date(item.pubDate),
                    thumbnail: item.thumbnail || item.enclosure?.link || this.extractImageFromContent(item.content)
                }));
            }
        } catch (e) {
            console.error("[MyRSS] Article fetch error:", e);
        }
        return [];
    }

    extractImageFromContent(content) {
        if (!content) return null;
        const match = content.match(/<img[^>]+src="([^">]+)"/);
        return match ? match[1] : null;
    }

    async loadArticles() {
        const el = this.elements;
        if (!el.articleContainer || !el.loadingOverlay) return;

        el.loadingOverlay.style.display = 'block';
        el.articleContainer.innerHTML = '';

        let allItems = [];
        try {
            if (this.activeFeedId === 'all') {
                const promises = this.feeds.map(f => this.fetchFeed(f.url));
                const results = await Promise.all(promises);
                allItems = results.flat();
            } else {
                const feed = this.feeds.find(f => f.id === this.activeFeedId);
                if (feed) {
                    if (el.feedTitle) el.feedTitle.innerText = feed.title;
                    allItems = await this.fetchFeed(feed.url);
                }
            }

            allItems.sort((a, b) => b.pubDate - a.pubDate);
            el.loadingOverlay.style.display = 'none';
            this.renderArticles(allItems.slice(0, 6));
        } catch (err) {
            console.error("[MyRSS] Load articles failed:", err);
            el.loadingOverlay.style.display = 'none';
        }
    }

    renderArticles(items) {
        const container = this.elements.articleContainer;
        if (!container) return;

        if (items.length === 0) {
            container.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:50px; color:var(--text-dim);">[ NO CHANNELS DETECTED. SCANNING IDLE. ]</div>`;
            return;
        }

        container.className = this.viewMode === 'grid' ? 'rss-grid' : 'rss-list';

        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'ag-card';
            card.innerHTML = `
                ${item.thumbnail ? `<div class="card-img"><img src="${item.thumbnail}" loading="lazy" /></div>` : ''}
                <div class="card-content">
                    <div class="card-meta">
                        <i>🕒</i> <span>${this.formatDate(item.pubDate)}</span>
                    </div>
                    <a href="${item.link}" target="_blank" class="card-link">${item.title}</a>
                </div>
            `;
            container.appendChild(card);
        });
    }

    renderFeeds() {
        const list = this.elements.feedList;
        if (!list) return;

        list.innerHTML = `
            <div class="feed-item ${this.activeFeedId === 'all' ? 'active' : ''}" onclick="window.rssApp.setActive('all')">
                <span class="icon">⊞</span> All News
            </div>
        `;

        this.feeds.forEach(f => {
            const item = document.createElement('div');
            item.className = `feed-item ${this.activeFeedId === f.id ? 'active' : ''}`;
            item.innerHTML = `
                <div class="feed-info" onclick="window.rssApp.setActive('${f.id}')">
                    <span class="icon">${f.icon === 'youtube' ? '▶' : '📄'}</span>
                    <span class="title">${f.title}</span>
                </div>
                <button class="delete-btn" onclick="window.rssApp.deleteFeed(event, '${f.id}')">×</button>
            `;
            list.appendChild(item);
        });
    }

    setActive(id) {
        console.log("[MyRSS] Setting active feed:", id);
        this.activeFeedId = id;
        this.renderFeeds();
        this.loadArticles();
    }

    deleteFeed(e, id) {
        e.stopPropagation();
        if (confirm('Delete this source?')) {
            this.feeds = this.feeds.filter(f => f.id !== id);
            if (this.activeFeedId === id) this.activeFeedId = 'all';
            this.save();
            this.renderFeeds();
        }
    }

    async handleAddFeed() {
        const el = this.elements;
        const url = el.feedUrlInput.value.trim();
        if (!url) return;
        
        el.saveFeedBtn.disabled = true;
        el.saveFeedBtn.innerText = 'SCANNING...';
        
        let finalUrl = url;
        if (!finalUrl.startsWith('http')) finalUrl = 'https://' + finalUrl;

        try {
            if (finalUrl.includes('youtube.com') || finalUrl.includes('youtu.be')) {
                const foundId = await this.findYoutubeId(finalUrl);
                if (foundId) finalUrl = `https://www.youtube.com/feeds/videos.xml?channel_id=${foundId}`;
            }

            const res = await fetch(`https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(finalUrl)}`);
            const data = await res.json();
            
            if (data.status === 'ok') {
                const newFeed = {
                    id: Date.now().toString(),
                    title: data.feed.title || 'New Feed',
                    url: finalUrl,
                    icon: finalUrl.includes('youtube') ? 'youtube' : 'news'
                };
                this.feeds.push(newFeed);
                this.save();
                el.addModal.style.display = 'none';
                el.feedUrlInput.value = '';
                this.renderFeeds();
                this.setActive(newFeed.id);
            } else {
                alert('COULD NOT RESOLVE RSS PATH.');
            }
        } catch (e) {
            alert('NETWORK ERROR DURING SCAN.');
        } finally {
            el.saveFeedBtn.disabled = false;
            el.saveFeedBtn.innerText = 'Add Feed';
        }
    }

    async findYoutubeId(url) {
        const proxies = [
            `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`,
            `https://corsproxy.io/?${encodeURIComponent(url)}`
        ];
        for (const proxy of proxies) {
            try {
                const res = await fetch(proxy);
                const html = proxy.includes('allorigins') ? (await res.json()).contents : (await res.text());
                const match = html.match(/"browseId":"(UC[\w-]{21,24})"/) || html.match(/"channelId":"(UC[\w-]{21,24})"/);
                if (match) return match[1];
            } catch (e) {}
        }
        return null;
    }

    handleExport() {
        const blob = new Blob([JSON.stringify(this.feeds)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'antigravity_feeds.json';
        a.click();
    }

    handleImport(e) {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const imported = JSON.parse(ev.target.result);
                if (Array.isArray(imported)) {
                    this.feeds = [...this.feeds, ...imported.filter(f => !this.feeds.some(existing => existing.url === f.url))];
                    this.save();
                    this.renderFeeds();
                    alert('IMPORT SUCCESS');
                }
            } catch (err) { alert('INVALID DATA STRUCTURE'); }
        };
        reader.readAsText(file);
    }

    formatDate(date) {
        const diff = (new Date() - date) / 1000;
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        return date.toLocaleDateString();
    }

    stripHtml(html) {
        const tmp = document.createElement("DIV");
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || "";
    }
}

// Global initialization
new RSSReader();
