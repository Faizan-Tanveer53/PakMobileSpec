// PakMobileSpec — Client-Side Interactivity (Search, Compare Tray, Theme, Variant Switcher)

(function () {
  // 1. THEME MANAGEMENT
  const htmlEl = document.documentElement;
  const savedTheme = localStorage.getItem('pakmobile_theme') || 'dark';
  htmlEl.setAttribute('data-theme', savedTheme);

  window.toggleSiteTheme = function () {
    const current = htmlEl.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    htmlEl.setAttribute('data-theme', next);
    localStorage.setItem('pakmobile_theme', next);
    const btn = document.getElementById('themeToggleBtn');
    if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
  };

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('themeToggleBtn');
    if (btn) {
      btn.textContent = (htmlEl.getAttribute('data-theme') || 'dark') === 'dark' ? '☀️' : '🌙';
    }
    initLiveSearch();
    initCompareTray();
  });

  // 2. LIVE INSTANT AUTOCOMPLETE SEARCH
  function initLiveSearch() {
    const input = document.getElementById('globalSearchInput');
    const dropdown = document.getElementById('globalSearchDropdown');
    if (!input || !dropdown) return;

    let debounceTimer = null;

    async function fetchSuggestions(query) {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        if (!res.ok) return;
        const data = await res.json();
        renderDropdown(data.results || [], query);
      } catch (err) {
        console.error('Search error:', err);
      }
    }

    function renderDropdown(items, query) {
      if (!items.length) {
        dropdown.innerHTML = `<div style="padding:1rem;color:var(--text-muted);font-size:0.86rem;">No phones found matching "${escapeHtml(query)}".</div>`;
        dropdown.classList.add('active');
        return;
      }

      const headerLabel = query.trim()
        ? `Matching Smartphones (${items.length})`
        : 'Popular Smartphones in Pakistan';

      let html = `<div style="padding:0.55rem 1rem;font-size:0.74rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted);background:var(--bg-secondary);">${headerLabel}</div>`;

      for (const p of items) {
        const statusBadge = p.is_demo_data
          ? `<span class="badge-demo" style="font-size:0.62rem;padding:0.1rem 0.4rem;">DEMO / SAMPLE</span>`
          : `<span class="badge-verified" style="font-size:0.62rem;padding:0.1rem 0.4rem;">VERIFIED DATA</span>`;

        html += `
          <a href="/phone/${p.slug}" class="search-item">
            <img src="${p.image_url}" alt="${escapeHtml(p.full_name)}" loading="lazy" />
            <div class="search-item-meta">
              <div class="search-item-title">${escapeHtml(p.full_name)} ${statusBadge}</div>
              <div class="search-item-specs">${escapeHtml(p.ram_display)} RAM • ${escapeHtml(p.storage_display)} • ${escapeHtml(p.processor || '')} ${p.is_5g ? '• 5G' : ''}</div>
            </div>
            <div class="search-item-price">${escapeHtml(p.price_formatted)}</div>
          </a>
        `;
      }
      html += `<a href="/phones?q=${encodeURIComponent(query)}" style="display:block;text-align:center;padding:0.65rem;font-size:0.82rem;font-weight:700;color:var(--accent-primary);background:var(--bg-secondary);">View All Search Results →</a>`;
      dropdown.innerHTML = html;
      dropdown.classList.add('active');
    }

    input.addEventListener('focus', () => {
      fetchSuggestions(input.value);
    });

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        fetchSuggestions(input.value);
      }, 160);
    });

    document.addEventListener('click', (e) => {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
  }

  // 3. FLOATING COMPARISON TRAY
  const COMPARE_KEY = 'pakmobile_compare_list';

  window.getCompareList = function () {
    try {
      return JSON.parse(localStorage.getItem(COMPARE_KEY) || '[]');
    } catch (e) {
      return [];
    }
  };

  window.toggleComparePhone = function (slug, name) {
    let list = window.getCompareList();
    const idx = list.findIndex((x) => x.slug === slug);
    if (idx > -1) {
      list.splice(idx, 1);
    } else {
      if (list.length >= 4) {
        alert('You can compare up to 4 phones at a time.');
        return;
      }
      list.push({ slug, name });
    }
    localStorage.setItem(COMPARE_KEY, JSON.stringify(list));
    updateCompareUI();
  };

  window.clearCompareList = function () {
    localStorage.removeItem(COMPARE_KEY);
    updateCompareUI();
  };

  function initCompareTray() {
    updateCompareUI();
  }

  function updateCompareUI() {
    const list = window.getCompareList();
    const tray = document.getElementById('compareFloatingTray');
    const itemsContainer = document.getElementById('compareTrayItems');
    const goLink = document.getElementById('compareTrayGoLink');

    // Sync all "+ Compare" buttons on page
    document.querySelectorAll('[data-compare-slug]').forEach((btn) => {
      const slug = btn.getAttribute('data-compare-slug');
      const inList = list.some((x) => x.slug === slug);
      if (inList) {
        btn.classList.add('in-compare');
        btn.textContent = '✓ In Compare';
      } else {
        btn.classList.remove('in-compare');
        btn.textContent = '+ Compare';
      }
    });

    if (!tray || !itemsContainer || !goLink) return;

    if (list.length === 0) {
      tray.classList.remove('visible');
      return;
    }

    tray.classList.add('visible');
    itemsContainer.innerHTML = list
      .map(
        (item) => `
      <span class="compare-tray-pill">
        ${escapeHtml(item.name)}
        <button type="button" onclick="toggleComparePhone('${item.slug}', '')" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-weight:800;">×</button>
      </span>
    `
      )
      .join('');

    const slugsParam = list.map((x) => x.slug).join(',');
    goLink.href = `/compare?phones=${encodeURIComponent(slugsParam)}`;
    goLink.textContent = `Compare (${list.length}) →`;
  }

  // 4. VARIANT PRICE SWITCHER ON DETAIL PAGE
  window.selectPhoneVariant = function (btnEl, priceFormatted, variantLabel) {
    document.querySelectorAll('.variant-btn').forEach((b) => b.classList.remove('active'));
    btnEl.classList.add('active');
    const priceDisplay = document.getElementById('dynamicPhonePrice');
    const labelDisplay = document.getElementById('dynamicVariantLabel');
    if (priceDisplay) priceDisplay.textContent = priceFormatted;
    if (labelDisplay) labelDisplay.textContent = variantLabel;
  };

  // 5. COMPARE PAGE DIFF HIGHLIGHTER
  window.toggleCompareDiffOnly = function (checkbox) {
    const rows = document.querySelectorAll('.compare-spec-row');
    rows.forEach((row) => {
      const cells = Array.from(row.querySelectorAll('td')).map((td) => td.textContent.trim().toLowerCase());
      const allSame = cells.length > 1 && cells.every((v) => v === cells[0]);
      if (checkbox.checked && allSame) {
        row.style.display = 'none';
      } else {
        row.style.display = '';
      }
    });
  };

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();
