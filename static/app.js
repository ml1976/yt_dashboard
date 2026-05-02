document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('timeline-container');
    const modal = document.getElementById('video-modal');
    const closeBtn = document.querySelector('#video-modal .close-btn');
    const playerContainer = document.getElementById('player-container');
    const categoryList = document.getElementById('category-list');
    const toast = document.getElementById('status-toast');
    const toastMessage = document.getElementById('toast-message');

    let currentData = [];
    let currentCategory = 'all';
    let currentFolder = 'all';
    
    // Settings state
    let settings = {};
    
    // Polling state
    let wasRssRunning = false;
    let wasCategoriesRunning = false;
    let wasLiveRunning = false;
    let wasDiscoveryRunning = false;
    let wasTrendingRunning = false;

    function fetchAndRender() {
        const sortValue = document.getElementById('sort-dropdown').value;
        container.innerHTML = '<div class="loading">Loading timeline...</div>';
        
        fetch(`/api/timeline?sort=${sortValue}&category=${encodeURIComponent(currentCategory)}&folder=${encodeURIComponent(currentFolder)}`)
            .then(response => response.json())
            .then(data => {
                // Update stats
                document.getElementById('stat-channels').innerText = `Loaded Channels: ${data.stats.channels}`;
                document.getElementById('stat-videos').innerText = `Total Videos: ${data.stats.videos}`;
                
                // Render Categories and Folders
                renderCategories(data.categories, data.custom_folders);
                
                currentData = data.timeline;
                renderTimeline(currentData);
            })
            .catch(error => {
                console.error('Error fetching timeline:', error);
                container.innerHTML = '<div class="loading" style="color: orange;">Server is busy (likely updating feeds in the background). Please wait a moment and try again...</div>';
            });
    }

    function renderCategories(categories, customFolders) {
        if (!categoryList) return;
        
        let html = `<li class="category-item ${currentCategory === 'all' && currentFolder === 'all' ? 'active' : ''}" data-category="all" data-type="category">All Channels</li>`;
        
        categories.forEach(cat => {
            if (cat) {
                html += `<li class="category-item ${currentCategory === cat ? 'active' : ''}" data-category="${cat}" data-type="category">${cat}</li>`;
            }
        });
        
        html += `<li class="category-item" data-category="fetch_new" data-type="action" style="margin-top: 20px; color: var(--accent); border: 1px solid var(--accent); text-align: center;">Scan for Genres</li>`;
        
        categoryList.innerHTML = html;
        
        const folderList = document.getElementById('custom-folder-list');
        if (folderList && customFolders) {
            let fHtml = '';
            customFolders.forEach(f => {
                fHtml += `<li class="category-item ${currentFolder === f ? 'active' : ''}" data-folder="${f}" data-type="folder">📁 ${f}</li>`;
            });
            folderList.innerHTML = fHtml;
        }
        
        // Add event listeners to category/folder items
        document.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const type = e.target.getAttribute('data-type') || e.target.closest('.category-item').getAttribute('data-type');
                
                if (type === 'action') {
                    fetch('/api/fetch_categories', { method: 'POST' })
                        .then(res => res.json())
                        .then(data => {
                            checkStatus(); // Force status check to show toast
                        });
                    return;
                }
                
                if (type === 'folder') {
                    currentFolder = e.target.getAttribute('data-folder') || e.target.closest('.category-item').getAttribute('data-folder');
                    currentCategory = 'all'; // Reset category
                } else {
                    currentCategory = e.target.getAttribute('data-category') || e.target.closest('.category-item').getAttribute('data-category');
                    currentFolder = 'all'; // Reset folder
                }
                
                fetchAndRender();
            });
        });
    }

    // Status polling
    function checkStatus() {
        fetch('/api/status')
            .then(res => res.json())
            .then(status => {
                const isRunning = status.rss_running || status.categories_running || status.live_running || status.discovery_running || status.trending_running;
                
                if (isRunning) {
                    toast.classList.remove('hidden');
                    let msg = [];
                    if (status.rss_running) msg.push("Syncing RSS");
                    if (status.live_running) msg.push("Fetching Live Streams");
                    if (status.discovery_running) msg.push("Finding New Content");
                    if (status.trending_running) msg.push("Fetching Trending");
                    if (status.categories_running) msg.push("Scanning genres");
                    toastMessage.innerText = msg.join(" & ") + "...";
                } else {
                    toast.classList.add('hidden');
                }
                
                // Auto-refresh if something just finished
                if (wasRssRunning && !status.rss_running) fetchAndRender();
                if (wasCategoriesRunning && !status.categories_running) fetchAndRender();
                if (wasLiveRunning && !status.live_running) fetchAndRenderRow('VIRTUAL_LIVE');
                if (wasDiscoveryRunning && !status.discovery_running) fetchAndRenderRow('VIRTUAL_DISCOVERY');
                if (wasTrendingRunning && !status.trending_running) fetchAndRenderRow('VIRTUAL_TRENDING');
                
                wasRssRunning = status.rss_running;
                wasCategoriesRunning = status.categories_running;
                wasLiveRunning = status.live_running;
                wasDiscoveryRunning = status.discovery_running;
                wasTrendingRunning = status.trending_running;
            })
            .catch(err => console.error("Status check failed", err));
    }
    
    // Check status every 3 seconds
    setInterval(checkStatus, 3000);
    checkStatus(); // Initial check

    // Initial load
    fetchAndRender();

    // Sort Dropdown Event
    document.getElementById('sort-dropdown').addEventListener('change', () => {
        fetchAndRender();
    });

    // Live Search Event
    document.getElementById('search-box').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = currentData.filter(ch => ch.name.toLowerCase().includes(query));
        renderTimeline(filtered);
    });

    function fetchAndRenderRow(channelId) {
        const sortValue = document.getElementById('sort-dropdown').value;
        fetch(`/api/timeline?sort=${sortValue}&category=${encodeURIComponent(currentCategory)}&folder=${encodeURIComponent(currentFolder)}`)
            .then(response => response.json())
            .then(data => {
                currentData = data.timeline;
                const channelData = currentData.find(c => c.channel_id === channelId);
                const oldRow = document.querySelector(`.channel-row[data-channel-id="${channelId}"]`);
                
                if (channelData) {
                    const newRow = createChannelRowElement(channelData);
                    if (oldRow) {
                        oldRow.replaceWith(newRow);
                    } else {
                        // Determine exactly where to insert this row in the DOM based on currentData order
                        const index = currentData.findIndex(c => c.channel_id === channelId);
                        if (index === 0) {
                            container.prepend(newRow);
                        } else {
                            // Find the row that comes right before it
                            const prevChannel = currentData[index - 1];
                            const prevRow = document.querySelector(`.channel-row[data-channel-id="${prevChannel.channel_id}"]`);
                            if (prevRow) {
                                prevRow.after(newRow);
                            } else {
                                // Fallback
                                container.prepend(newRow);
                            }
                        }
                    }
                } else if (oldRow) {
                    // Channel is completely empty now (e.g. last video removed from Watch Later)
                    oldRow.remove();
                }
            });
    }

    function createChannelRowElement(channel) {
        const row = document.createElement('div');
        row.className = 'channel-row';
        row.dataset.channelId = channel.channel_id;
        
        // Create header
        const header = document.createElement('div');
        header.className = 'channel-header';
        header.style.display = 'flex';
        header.style.alignItems = 'center';
        header.style.gap = '15px';
        
        let folderBadge = channel.custom_folder ? `<span class="folder-badge">${channel.custom_folder}</span>` : '';
        
        const headerLeft = document.createElement('div');
        headerLeft.style.display = 'flex';
        headerLeft.style.alignItems = 'center';
        headerLeft.style.gap = '10px';
        headerLeft.innerHTML = `
            <a href="${channel.url}" target="_blank" class="channel-name">${channel.name}</a>
            ${folderBadge}
            <span class="folder-icon" data-id="${channel.channel_id}" title="Assign to Custom Folder">📁</span>
        `;
        
        const scrollControls = document.createElement('div');
        scrollControls.className = 'header-scroll-controls';
        scrollControls.style.display = 'flex';
        scrollControls.style.gap = '8px';
        
        const scrollLeftBtn = document.createElement('button');
        scrollLeftBtn.className = 'header-scroll-btn';
        scrollLeftBtn.innerHTML = '&#10094;';
        scrollLeftBtn.title = 'Scroll Left';
        scrollLeftBtn.style.visibility = 'hidden'; // Use visibility instead of display so it reserves space
        
        const scrollRightBtn = document.createElement('button');
        scrollRightBtn.className = 'header-scroll-btn';
        scrollRightBtn.innerHTML = '&#10095;';
        scrollRightBtn.title = 'Scroll Right';
        
        scrollControls.appendChild(scrollLeftBtn);
        scrollControls.appendChild(scrollRightBtn);
        
        header.appendChild(headerLeft);
        header.appendChild(scrollControls);
        row.appendChild(header);
        
        // Attach folder icon event
        const fIcon = headerLeft.querySelector('.folder-icon');
        if (fIcon && !channel.channel_id.startsWith('VIRTUAL_')) {
            fIcon.addEventListener('click', () => {
                const folderName = prompt(`Enter custom folder name for ${channel.name} (leave empty to remove):`, channel.custom_folder || '');
                if (folderName !== null) {
                    fetch('/api/set_custom_folder', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ channel_id: channel.channel_id, custom_folder: folderName.trim() })
                    }).then(() => fetchAndRender());
                }
            });
        } else if (fIcon) {
            fIcon.style.display = 'none'; // Don't show folder icon for virtual channels
        }
        
        // Create videos container (horizontal scroll)
        const vContainer = document.createElement('div');
        vContainer.className = 'videos-container';
        
        let updateScrollButtons = () => {};
        
        if (channel.videos.length === 0) {
            vContainer.innerHTML = '<div style="padding: 20px; color: #888; font-style: italic;">No videos currently in this queue.</div>';
        } else {
            // 3 videos = 3 * (280 width + 15 gap) = 885px
            scrollLeftBtn.addEventListener('click', () => {
                vContainer.scrollBy({ left: -885, behavior: 'smooth' });
            });
            scrollRightBtn.addEventListener('click', () => {
                vContainer.scrollBy({ left: 885, behavior: 'smooth' });
            });
            
            updateScrollButtons = () => {
                scrollLeftBtn.style.visibility = vContainer.scrollLeft > 5 ? 'visible' : 'hidden';
                // 5px margin of error for browser rendering sub-pixels
                scrollRightBtn.style.visibility = vContainer.scrollLeft < (vContainer.scrollWidth - vContainer.clientWidth - 5) ? 'visible' : 'hidden';
            };
            
            vContainer.addEventListener('scroll', updateScrollButtons);
            
            channel.videos.forEach(video => {
            const card = document.createElement('div');
            card.className = 'video-card';
            if (video.is_watched) {
                card.classList.add('watched');
            }
            if (video.muted) {
                card.classList.add('muted');
            }
            
            // Format relative time (e.g., "2 days ago")
            const timeAgo = formatTimeAgo(new Date(video.published_at));
            
            let mutedOverlay = video.muted ? `<div class="muted-overlay">Muted: ${video.muted_reason}</div>` : '';
            
            card.innerHTML = `
                <div class="video-thumb">
                    <img src="${video.thumbnail_url || 'https://via.placeholder.com/280x157?text=No+Thumbnail'}" alt="Thumbnail" loading="lazy">
                    ${mutedOverlay}
                    <div class="watch-later-btn ${video.is_watch_later ? 'active' : ''}" title="Watch Later">+</div>
                    <div class="favorite-star ${video.is_favorite ? 'active' : ''}">★</div>
                </div>
                <div class="video-info">
                    <div class="video-title" title="${video.title}">${video.title}</div>
                    <div class="video-meta">${timeAgo}</div>
                </div>
            `;
            
            // Strip 'LIVE_' prefix if it exists so favorites/watch later/clicks sync correctly
            let actualVideoId = video.video_id;
            if (actualVideoId.startsWith('LIVE_')) {
                actualVideoId = actualVideoId.substring(5);
            }
            
            // Handle favorite click separately
            const star = card.querySelector('.favorite-star');
            star.addEventListener('click', (e) => {
                e.stopPropagation();
                const newFavStatus = star.classList.contains('active') ? 0 : 1;
                star.classList.toggle('active');
                
                fetch('/api/toggle_favorite', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_id: actualVideoId, is_favorite: newFavStatus })
                }).then(() => {
                    const oldRow = document.querySelector('.channel-row[data-channel-id="VIRTUAL_FAVORITES"]');
                    if (oldRow) {
                        fetchAndRenderRow('VIRTUAL_FAVORITES');
                    } else if (newFavStatus === 1) {
                        fetchAndRenderRow('VIRTUAL_FAVORITES'); // Re-render just the row (it will inject itself)
                    }
                });
            });
            
            // Handle watch later click
            const wlBtn = card.querySelector('.watch-later-btn');
            wlBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const newWlStatus = wlBtn.classList.contains('active') ? 0 : 1;
                wlBtn.classList.toggle('active');
                
                fetch('/api/toggle_watch_later', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_id: actualVideoId, is_watch_later: newWlStatus })
                }).then(() => {
                    const oldRow = document.querySelector('.channel-row[data-channel-id="VIRTUAL_WATCH_LATER"]');
                    if (oldRow) {
                        fetchAndRenderRow('VIRTUAL_WATCH_LATER');
                    } else if (newWlStatus === 1) {
                        fetchAndRenderRow('VIRTUAL_WATCH_LATER'); // Re-render just the row (it will inject itself)
                    }
                });
            });
            
            // Attach click event to open modal
            card.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Track the click (if not watched already)
                if (!video.is_watched) {
                    card.classList.add('watched');
                    video.is_watched = true;
                    
                    fetch('/api/track_click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ channel_id: channel.channel_id, video_id: actualVideoId })
                    });
                }
                
                openModal(actualVideoId);
            });
            
            vContainer.appendChild(card);
        });
        }
        
        if (channel.channel_id === 'VIRTUAL_HOME') {
            // No "Load Older" for the dynamic home row
        } else if (channel.channel_id === 'VIRTUAL_DISCOVERY') {
            const loadOlderBtn = document.createElement('div');
            loadOlderBtn.className = 'load-older-card';
            loadOlderBtn.innerHTML = `
                <div class="load-older-content">
                    <div class="load-icon">↻</div>
                    <div>Find New Videos</div>
                </div>
            `;
            loadOlderBtn.addEventListener('click', () => {
                const icon = loadOlderBtn.querySelector('.load-icon');
                icon.style.animation = 'spin 1s linear infinite';
                fetch('/api/fetch_discovery', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => checkStatus());
            });
            vContainer.appendChild(loadOlderBtn);
        } else if (channel.channel_id === 'VIRTUAL_TRENDING') {
            const loadOlderBtn = document.createElement('div');
            loadOlderBtn.className = 'load-older-card';
            loadOlderBtn.innerHTML = `
                <div class="load-older-content">
                    <div class="load-icon">↻</div>
                    <div>Refresh Trending</div>
                </div>
            `;
            loadOlderBtn.addEventListener('click', () => {
                const icon = loadOlderBtn.querySelector('.load-icon');
                icon.style.animation = 'spin 1s linear infinite';
                fetch('/api/fetch_trending', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => checkStatus());
            });
            vContainer.appendChild(loadOlderBtn);
        } else if (channel.channel_id === 'VIRTUAL_LIVE') {
            const loadOlderBtn = document.createElement('div');
            loadOlderBtn.className = 'load-older-card';
            loadOlderBtn.innerHTML = `
                <div class="load-older-content">
                    <div class="load-icon">↻</div>
                    <div>Refresh Live Streams</div>
                </div>
            `;
            loadOlderBtn.addEventListener('click', () => {
                const icon = loadOlderBtn.querySelector('.load-icon');
                icon.style.animation = 'spin 1s linear infinite';
                fetch('/api/fetch_live', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => checkStatus());
            });
            vContainer.appendChild(loadOlderBtn);
        } else if (channel.channel_id === 'VIRTUAL_FAVORITES' || channel.channel_id === 'VIRTUAL_WATCH_LATER') {
            // No special load older for queue rows
        } else {
            const loadOlderBtn = document.createElement('div');
            loadOlderBtn.className = 'load-older-card';
            loadOlderBtn.innerHTML = `
                <div class="load-older-content">
                    <div class="load-icon">↻</div>
                    <div>Load Older Videos</div>
                </div>
            `;
            loadOlderBtn.addEventListener('click', () => {
                loadOlderBtn.innerHTML = '<div class="loading" style="padding:0; margin:auto;">Loading...</div>';
                fetch('/api/load_older?channel_id=' + encodeURIComponent(channel.channel_id))
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message + " Wait a minute and refresh the page.");
                    })
                    .catch(err => {
                        alert('Error requesting older videos');
                        loadOlderBtn.innerHTML = `
                            <div class="load-older-content">
                                <div class="load-icon">↻</div>
                                <div>Load Older Videos</div>
                            </div>
                        `;
                    });
            });
            vContainer.appendChild(loadOlderBtn);
        }
        
        row.appendChild(vContainer);
        
        // Check initial scroll state after dom update
        setTimeout(updateScrollButtons, 100);
        
        return row;
    }

    function renderTimeline(channels) {
        container.innerHTML = ''; // Clear loading text
        
        if (channels.length === 0) {
            container.innerHTML = '<div class="loading">No channels or videos found in the database yet. Run the historical scraper!</div>';
            return;
        }

        channels.forEach(channel => {
            const row = createChannelRowElement(channel);
            container.appendChild(row);
        });
    }

    function openModal(videoId) {
        // Embed YouTube iframe
        playerContainer.innerHTML = `
            <iframe 
                src="https://www.youtube.com/embed/${videoId}?autoplay=1" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        `;
        modal.style.display = 'flex';
    }

    function closeModal() {
        modal.style.display = 'none';
        playerContainer.innerHTML = ''; // Stop video playback
    }

    // Settings logic
    const settingsModal = document.getElementById('settings-modal');
    const settingsBtn = document.getElementById('btn-settings');
    const settingsCloseBtn = document.querySelector('.settings-close-btn');
    const saveSettingsBtn = document.getElementById('btn-save-settings');
    const mutedKeywordsInput = document.getElementById('muted-keywords-input');
    
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            fetch('/api/settings')
                .then(res => res.json())
                .then(data => {
                    if (data.muted_keywords) {
                        mutedKeywordsInput.value = data.muted_keywords.join(', ');
                    } else {
                        mutedKeywordsInput.value = '';
                    }
                    settingsModal.style.display = 'flex';
                });
        });
    }
    
    if (settingsCloseBtn) {
        settingsCloseBtn.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });
    }
    
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            const words = mutedKeywordsInput.value.split(',').map(w => w.trim()).filter(w => w.length > 0);
            
            saveSettingsBtn.disabled = true;
            saveSettingsBtn.innerText = "Saving...";
            
            fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ muted_keywords: words })
            })
            .then(() => {
                settingsModal.style.display = 'none';
                saveSettingsBtn.disabled = false;
                saveSettingsBtn.innerText = "Save Settings";
                fetchAndRender(); // re-render to apply new muting
            });
        });
    }
    
    // Analytics logic
    const analyticsModal = document.getElementById('analytics-modal');
    const analyticsBtn = document.getElementById('btn-analytics');
    const analyticsCloseBtn = document.querySelector('.analytics-close-btn');
    
    if (analyticsBtn) {
        analyticsBtn.addEventListener('click', () => {
            // Calculate stats from currentData
            let topChannels = [...currentData].filter(c => !c.channel_id.startsWith('VIRTUAL_')).sort((a, b) => b.local_views - a.local_views).slice(0, 10);
            let totalViews = 0;
            let genreCounts = {};
            
            currentData.forEach(c => {
                if (!c.channel_id.startsWith('VIRTUAL_')) {
                    totalViews += c.local_views;
                    if (c.category) {
                        genreCounts[c.category] = (genreCounts[c.category] || 0) + c.local_views;
                    }
                }
            });
            
            let topGenres = Object.entries(genreCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
            
            document.getElementById('analytics-total-views').innerText = totalViews.toLocaleString() + ' Views Recorded';
            
            const channelsList = document.getElementById('analytics-top-channels');
            channelsList.innerHTML = topChannels.map((c, i) => `<li style="padding: 5px 0;"><strong>#${i+1}</strong> ${c.name} - <span style="color: var(--accent);">${c.local_views.toLocaleString()} views</span></li>`).join('');
            
            const genresList = document.getElementById('analytics-top-genres');
            genresList.innerHTML = topGenres.map((g, i) => `<li style="padding: 5px 0;"><strong>#${i+1}</strong> ${g[0]} - <span style="color: var(--accent);">${g[1].toLocaleString()} views</span></li>`).join('');
            
            analyticsModal.style.display = 'flex';
        });
    }
    
    if (analyticsCloseBtn) {
        analyticsCloseBtn.addEventListener('click', () => {
            analyticsModal.style.display = 'none';
        });
    }
    if (analyticsModal) {
        analyticsModal.addEventListener('click', (e) => {
            if (e.target === analyticsModal) {
                analyticsModal.style.display = 'none';
            }
        });
    }
    
    // Modal close events
    closeBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
    if (settingsModal) {
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) {
                settingsModal.style.display = 'none';
            }
        });
    }

    // Helper: Time ago formatter
    function formatTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + " years ago";
        
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + " months ago";
        
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + " days ago";
        
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + " hours ago";
        
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + " minutes ago";
        
        return "Just now";
    }

    // Button event listeners
    const btnRefresh = document.getElementById('btn-refresh');
    const btnScrape = document.getElementById('btn-scrape');
    const btnAddChannel = document.getElementById('btn-add-channel');
    const inputAddChannel = document.getElementById('add-channel-input');

    if (btnAddChannel && inputAddChannel) {
        btnAddChannel.addEventListener('click', () => {
            const url = inputAddChannel.value.trim();
            if (!url) return;
            
            btnAddChannel.disabled = true;
            btnAddChannel.innerText = "Adding...";
            
            fetch('/api/add_channel', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message);
                    inputAddChannel.value = '';
                    fetchAndRender();
                } else {
                    alert(data.message || 'Error adding channel');
                }
            })
            .catch(err => {
                alert('Network or Server Error');
            })
            .finally(() => {
                btnAddChannel.disabled = false;
                btnAddChannel.innerText = "Add Channel";
            });
        });
    }

    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            btnRefresh.disabled = true;
            btnRefresh.innerText = "Updating...";
            fetch('/api/scrape_rss', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    checkStatus(); // Instantly show toast
                    setTimeout(() => {
                        btnRefresh.disabled = false;
                        btnRefresh.innerText = "Update from RSS";
                    }, 3000);
                })
                .catch(err => {
                    alert('Server is updating feeds in the background. Please wait a moment and refresh manually.');
                    btnRefresh.disabled = false;
                    btnRefresh.innerText = "Update from RSS";
                });
        });
    }

    if (btnScrape) {
        btnScrape.addEventListener('click', () => {
            btnScrape.disabled = true;
            btnScrape.innerText = "Scraping...";
            fetch('/api/scrape_historical', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    alert(data.message + " Wait a minute and refresh the page.");
                    btnScrape.disabled = false;
                    btnScrape.innerText = "Scrape 5 More Channels";
                })
                .catch(err => {
                    alert('Error starting scraper');
                    btnScrape.disabled = false;
                    btnScrape.innerText = "Scrape 5 More Channels";
                });
        });
    }
});
