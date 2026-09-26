// PakMobileSpec — Admin Panel Interactive Operations (Verification-Safe CRUD & Source Provenance)

async function quickUpdatePrice(phoneId) {
  const inputEl = document.getElementById(`price-input-${phoneId}`);
  const feedbackEl = document.getElementById(`price-feedback-${phoneId}`);
  const updatedCellEl = document.getElementById(`updated-cell-${phoneId}`);

  if (!inputEl) return;
  const newPrice = parseInt(inputEl.value, 10);
  if (isNaN(newPrice) || newPrice < 0) {
    alert('Please enter a valid price in PKR.');
    return;
  }

  const formData = new FormData();
  formData.append('price_pkr', newPrice);
  // VERIFICATION SAFETY: Updating the price alone does NOT auto-verify DEMO/SAMPLE data.
  formData.append('mark_verified', 0);

  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/quick-price`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      if (feedbackEl) {
        feedbackEl.style.display = 'block';
        feedbackEl.textContent = `✓ Price Saved (${data.price_formatted})`;
        setTimeout(() => {
          feedbackEl.style.display = 'none';
        }, 3500);
      }
      if (updatedCellEl && data.updated_at) {
        updatedCellEl.innerHTML = `<strong style="color:var(--text-primary);display:block;">${data.updated_at}</strong><span>${data.updated_timestamp || ''}</span>`;
      }
    } else {
      alert(data.error || 'Failed to update price');
    }
  } catch (err) {
    alert('Network error while updating price.');
  }
}

function openVerifyModal(phoneId, modelName, currentStatus, sourceName, sourceUrl, verifNotes) {
  const modal = document.getElementById('verifyModal');
  if (!modal) return;
  document.getElementById('verifyModalPhoneId').value = phoneId;
  document.getElementById('verifyModalPhoneTitle').textContent = `Phone: ${modelName} (#${phoneId})`;
  document.getElementById('verifyModalStatus').value =
    currentStatus === 'VERIFIED' ? 'VERIFIED' : 'DEMO/SAMPLE';
  document.getElementById('verifyModalSourceName').value = sourceName || '';
  document.getElementById('verifyModalSourceUrl').value = sourceUrl || '';
  document.getElementById('verifyModalNotes').value = verifNotes || '';
  modal.showModal();
}

async function submitVerifyModal(event) {
  event.preventDefault();
  const phoneId = document.getElementById('verifyModalPhoneId').value;
  const form = document.getElementById('verifyModalForm');
  const formData = new FormData(form);

  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/verification`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      const badgeWrapEl = document.getElementById(`status-badge-wrap-${phoneId}`);
      const sourceLabelEl = document.getElementById(`source-label-${phoneId}`);
      const updatedCellEl = document.getElementById(`updated-cell-${phoneId}`);

      if (badgeWrapEl) {
        badgeWrapEl.innerHTML = data.is_demo_data
          ? `<span class="badge-demo">DEMO / SAMPLE</span>`
          : `<span class="badge-verified">✓ VERIFIED DATA</span>`;
      }
      if (sourceLabelEl) {
        sourceLabelEl.innerHTML = `<strong>Source:</strong> ${data.source_name}`;
      }
      if (updatedCellEl && data.updated_at) {
        updatedCellEl.innerHTML = `<strong style="color:var(--text-primary);display:block;">${data.updated_at}</strong><span>${data.updated_timestamp || ''}</span>`;
      }
      document.getElementById('verifyModal').close();
    } else {
      alert(data.error || 'Failed to update verification details');
    }
  } catch (err) {
    alert('Network error updating verification details.');
  }
}

async function toggleVerifyStatus(phoneId) {
  const badgeWrapEl = document.getElementById(`status-badge-wrap-${phoneId}`);
  const sourceLabelEl = document.getElementById(`source-label-${phoneId}`);
  const updatedCellEl = document.getElementById(`updated-cell-${phoneId}`);
  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/toggle-verify`, {
      method: 'POST',
    });
    const data = await res.json();
    if (data.success) {
      if (badgeWrapEl) {
        badgeWrapEl.innerHTML = data.is_demo_data
          ? `<span class="badge-demo">DEMO / SAMPLE</span>`
          : `<span class="badge-verified">✓ VERIFIED DATA</span>`;
      }
      if (sourceLabelEl && data.source_name) {
        sourceLabelEl.innerHTML = `<strong>Source:</strong> ${data.source_name}`;
      }
      if (updatedCellEl && data.updated_at) {
        updatedCellEl.innerHTML = `<strong style="color:var(--text-primary);display:block;">${data.updated_at}</strong><span>${data.updated_timestamp || ''}</span>`;
      }
    }
  } catch (err) {
    console.error(err);
  }
}

async function duplicatePhone(phoneId) {
  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/duplicate`, {
      method: 'POST',
    });
    const data = await res.json();
    if (data.success && data.new_id) {
      window.location.href = `/admin/phone/${data.new_id}/edit`;
    }
  } catch (err) {
    alert('Failed to duplicate phone.');
  }
}

async function deletePhone(phoneId, fullName) {
  if (!confirm(`Are you sure you want to delete "${fullName}" from the database?`)) {
    return;
  }
  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/delete`, {
      method: 'POST',
    });
    const data = await res.json();
    if (data.success) {
      const row = document.getElementById(`admin-row-${phoneId}`);
      if (row) row.remove();
    }
  } catch (err) {
    alert('Failed to delete phone.');
  }
}

function recalculateFormSaleDiscount() {
  const regInput = document.getElementById('regularPriceInput');
  const origReadonly = document.getElementById('originalPriceReadonly');
  const salePriceInput = document.getElementById('salePriceInput');
  const badgeEl = document.getElementById('liveDiscountBadge');
  const errEl = document.getElementById('saleFormErrorBanner');
  const clearHidden = document.getElementById('clearSaleHiddenInput');

  if (clearHidden) clearHidden.value = '0';
  if (errEl) errEl.style.display = 'none';

  const regPrice = regInput ? parseInt(regInput.value, 10) || 0 : 0;
  if (origReadonly) {
    origReadonly.value = `Rs. ${regPrice.toLocaleString('en-PK')}`;
  }

  const salePrice = salePriceInput ? parseInt(salePriceInput.value, 10) || 0 : 0;
  if (badgeEl) {
    if (regPrice > 0 && salePrice > 0 && salePrice < regPrice) {
      const pct = Math.max(1, Math.min(99, Math.round(((regPrice - salePrice) / regPrice) * 100)));
      badgeEl.textContent = `Discount: ${pct}% OFF`;
      badgeEl.style.color = '#34d399';
    } else {
      badgeEl.textContent = 'Discount: 0% OFF';
    }
  }
}

function clearSaleFormFields() {
  const chk = document.getElementById('saleActiveCheckbox');
  const salePriceInput = document.getElementById('salePriceInput');
  const saleLabelInput = document.getElementById('saleLabelInput');
  const saleStartInput = document.getElementById('saleStartInput');
  const saleEndInput = document.getElementById('saleEndInput');
  const clearHidden = document.getElementById('clearSaleHiddenInput');
  const badgeEl = document.getElementById('liveDiscountBadge');
  const errEl = document.getElementById('saleFormErrorBanner');

  if (chk) chk.checked = false;
  if (salePriceInput) salePriceInput.value = '';
  if (saleLabelInput) saleLabelInput.value = '';
  if (saleStartInput) saleStartInput.value = '';
  if (saleEndInput) saleEndInput.value = '';
  if (clearHidden) clearHidden.value = '1';
  if (badgeEl) badgeEl.textContent = 'Discount: 0% OFF';
  if (errEl) errEl.style.display = 'none';
}

async function submitFullPhoneForm(event) {
  event.preventDefault();
  const form = event.target;
  const errEl = document.getElementById('saleFormErrorBanner');
  if (errEl) errEl.style.display = 'none';

  const chk = document.getElementById('saleActiveCheckbox');
  const regInput = document.getElementById('regularPriceInput');
  const salePriceInput = document.getElementById('salePriceInput');
  const saleStartInput = document.getElementById('saleStartInput');
  const saleEndInput = document.getElementById('saleEndInput');

  const regPrice = regInput ? parseInt(regInput.value, 10) || 0 : 0;
  const saleEnabled = chk && chk.checked;
  const salePriceRaw = salePriceInput ? salePriceInput.value.trim() : '';
  const salePrice = salePriceRaw ? parseInt(salePriceRaw, 10) : null;

  if (saleEnabled && (salePrice === null || isNaN(salePrice))) {
    if (errEl) {
      errEl.textContent = 'Sale Price (PKR) is required when Enable Sale is checked.';
      errEl.style.display = 'block';
    } else {
      alert('Sale Price (PKR) is required when Enable Sale is checked.');
    }
    return;
  }

  if (salePrice !== null && !isNaN(salePrice)) {
    if (salePrice <= 0) {
      if (errEl) {
        errEl.textContent = 'Sale Price (PKR) must be greater than 0.';
        errEl.style.display = 'block';
      }
      return;
    }
    if (salePrice >= regPrice) {
      if (errEl) {
        errEl.textContent = `Sale Price (Rs. ${salePrice.toLocaleString()}) must be strictly less than Original Price (Rs. ${regPrice.toLocaleString()}).`;
        errEl.style.display = 'block';
      }
      return;
    }
  }

  if (saleStartInput && saleEndInput && saleStartInput.value && saleEndInput.value) {
    if (new Date(saleEndInput.value) <= new Date(saleStartInput.value)) {
      if (errEl) {
        errEl.textContent = 'Sale End Date/Time must be after Sale Start Date/Time.';
        errEl.style.display = 'block';
      }
      return;
    }
  }

  const formData = new FormData(form);

  try {
    const res = await fetch('/admin/api/phone/save', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      window.location.href = `/phone/${data.slug}`;
    } else {
      if (errEl) {
        errEl.textContent = data.error || 'Error saving phone specifications.';
        errEl.style.display = 'block';
      } else {
        alert(data.error || 'Error saving phone specifications.');
      }
    }
  } catch (err) {
    alert('Network error saving phone.');
  }
}

function openSaleModal(phoneId, fullTitle, regularPrice, saleActive, salePrice, saleLabel, saleStart, saleEnd) {
  const modal = document.getElementById('saleModal');
  if (!modal) return;

  const regInput = document.getElementById(`price-input-${phoneId}`);
  const currentRegPrice = regInput ? parseInt(regInput.value, 10) || regularPrice : regularPrice;

  document.getElementById('saleModalPhoneId').value = phoneId;
  document.getElementById('saleModalRegularPrice').value = currentRegPrice;
  document.getElementById('saleModalPhoneTitle').textContent = `${fullTitle} (#${phoneId})`;
  document.getElementById('saleModalRegularDisplay').textContent = `Rs. ${currentRegPrice.toLocaleString('en-PK')}`;
  document.getElementById('saleModalActive').checked = Number(saleActive) === 1;
  document.getElementById('saleModalPrice').value = salePrice ? salePrice : '';
  document.getElementById('saleModalLabel').value = saleLabel ? saleLabel : '';
  document.getElementById('saleModalStart').value = saleStart ? saleStart : '';
  document.getElementById('saleModalEnd').value = saleEnd ? saleEnd : '';

  const errEl = document.getElementById('saleModalError');
  if (errEl) errEl.style.display = 'none';

  recalculateModalSaleDiscount();
  modal.showModal();
}

function recalculateModalSaleDiscount() {
  const regPrice = parseInt(document.getElementById('saleModalRegularPrice').value, 10) || 0;
  const salePrice = parseInt(document.getElementById('saleModalPrice').value, 10) || 0;
  const badge = document.getElementById('saleModalLiveDiscount');
  if (!badge) return;

  if (regPrice > 0 && salePrice > 0 && salePrice < regPrice) {
    const pct = Math.max(1, Math.min(99, Math.round(((regPrice - salePrice) / regPrice) * 100)));
    badge.textContent = `Discount: ${pct}% OFF`;
  } else {
    badge.textContent = 'Discount: 0% OFF';
  }
}

async function submitSaleModal(event) {
  event.preventDefault();
  const phoneId = document.getElementById('saleModalPhoneId').value;
  const regPrice = parseInt(document.getElementById('saleModalRegularPrice').value, 10) || 0;
  const saleActive = document.getElementById('saleModalActive').checked ? 1 : 0;
  const salePriceVal = document.getElementById('saleModalPrice').value.trim();
  const saleLabel = document.getElementById('saleModalLabel').value.trim();
  const saleStart = document.getElementById('saleModalStart').value.trim();
  const saleEnd = document.getElementById('saleModalEnd').value.trim();
  const errEl = document.getElementById('saleModalError');

  if (errEl) errEl.style.display = 'none';

  if (saleActive === 1 && !salePriceVal) {
    if (errEl) {
      errEl.textContent = 'Sale Price (PKR) is required when Enable Sale Offer is checked.';
      errEl.style.display = 'block';
    }
    return;
  }

  if (salePriceVal) {
    const sp = parseInt(salePriceVal, 10);
    if (isNaN(sp) || sp <= 0 || sp >= regPrice) {
      if (errEl) {
        errEl.textContent = `Sale Price must be greater than 0 and strictly less than Rs. ${regPrice.toLocaleString('en-PK')}.`;
        errEl.style.display = 'block';
      }
      return;
    }
  }

  const formData = new FormData();
  formData.append('sale_active', saleActive);
  formData.append('sale_price_pkr', salePriceVal);
  formData.append('sale_label', saleLabel);
  formData.append('sale_start_at', saleStart);
  formData.append('sale_end_at', saleEnd);
  formData.append('clear_sale', 0);

  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/sale`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById('saleModal').close();
      window.location.reload();
    } else {
      if (errEl) {
        errEl.textContent = data.error || 'Failed to save sale offer.';
        errEl.style.display = 'block';
      }
    }
  } catch (err) {
    if (errEl) {
      errEl.textContent = 'Network error saving sale offer.';
      errEl.style.display = 'block';
    }
  }
}

async function clearModalPhoneSale() {
  const phoneId = document.getElementById('saleModalPhoneId').value;
  const formData = new FormData();
  formData.append('clear_sale', 1);

  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/sale`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById('saleModal').close();
      window.location.reload();
    } else {
      alert(data.error || 'Failed to clear sale.');
    }
  } catch (err) {
    alert('Network error clearing sale.');
  }
}

async function quickToggleSale(phoneId, targetActive) {
  const formData = new FormData();
  formData.append('sale_active', targetActive);

  try {
    const res = await fetch(`/admin/api/phone/${phoneId}/sale`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      window.location.reload();
    } else {
      alert(data.error || 'Cannot enable sale without configuring a valid sale price.');
    }
  } catch (err) {
    alert('Network error updating sale status.');
  }
}

async function saveBrandForm(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);

  try {
    const res = await fetch('/admin/api/brand/save', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      window.location.reload();
    } else {
      alert(data.error || 'Failed to save brand.');
    }
  } catch (err) {
    alert('Error saving brand.');
  }
}

async function uploadPhoneImageFile(fileInput) {
  if (!fileInput.files || !fileInput.files[0]) return;
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    const res = await fetch('/admin/api/upload-image', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.success && data.image_url) {
      const urlInput = document.getElementById('phoneImageUrlInput');
      if (urlInput) urlInput.value = data.image_url;
    } else {
      alert(data.error || 'Upload failed');
    }
  } catch (err) {
    alert('Error uploading image.');
  }
}
