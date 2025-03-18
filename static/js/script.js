/*
 * SPDX-FileCopyrightText: 2024 Davíð Berman <davidjberman@gmail.com>
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

// ===========================================================================

const initializeOpenSectionsBasedOnURL = () => {
  const hash = document.location.hash;
  if (hash.length > 1) {
    const el = document.querySelector(hash);
    if (el) {
      el.click();
    }
  }
};

// ---------------------------------------------------------------------------

const SCROLLSTATE_TTL = 5 * 1000; // 5 seconds

const saveScrollState = () => {
  const scrollState = {
    y: window.scrollY,
    hash: decodeURIComponent(document.location.hash.slice(1)),
    expires: Date.now() + SCROLLSTATE_TTL,
  };
  sessionStorage.setItem('scrollState', JSON.stringify(scrollState));
};

const restoreTempSavedScrollState = () => {
  let scrollState;
  try {
    scrollState = JSON.parse(sessionStorage.getItem('scrollState') || 'null');
  } finally {
    sessionStorage.removeItem('scrollState');
  }
  if (scrollState && Date.now() < scrollState.expires) {
    document.location.hash = scrollState.hash;
    initializeOpenSectionsBasedOnURL();
    window.scrollTo(0, scrollState.y);
  }
};

// ---------------------------------------------------------------------------

let currentlyActiveHverfi;
let currentlyActiveDevice;

const handleHverfiButtonClick = (event) => {
  const newHverfi = event.currentTarget;

  if (currentlyActiveHverfi) {
    currentlyActiveHverfi.parentElement.classList.remove('active');
  }
  if (currentlyActiveDevice) {
    currentlyActiveDevice.parentElement.classList.remove('active');
    currentlyActiveDevice = null;
  }
  if (currentlyActiveHverfi === newHverfi) {
    currentlyActiveHverfi = null;
    document.location.hash = '';
    return;
  }
  newHverfi.parentElement.classList.add('active');
  currentlyActiveHverfi = newHverfi;
  document.location.hash = newHverfi.id;
};

const handleDeviceButtonClick = (event) => {
  const newDevice = event.currentTarget;
  const newHverfi = newDevice
    .closest('.hverfi-section')
    .querySelector('button.collapsible');

  if (currentlyActiveDevice) {
    currentlyActiveDevice.parentElement.classList.remove('active');
  }
  if (currentlyActiveHverfi && currentlyActiveHverfi !== newHverfi) {
    currentlyActiveHverfi.parentElement.classList.remove('active');
  }
  if (currentlyActiveDevice === newDevice) {
    currentlyActiveDevice = null;
    document.location.hash = '';
    return;
  }
  newDevice.parentElement.classList.add('active');
  newHverfi.parentElement.classList.add('active');
  currentlyActiveDevice = newDevice;
  currentlyActiveHverfi = newHverfi;
  document.location.hash = newDevice.id;
};

// ===========================================================================

const main = () => {
  // When links inside buttons get clicked, let's prevent the parent button
  // also being clicked, which would cause the collapsible to toggle.
  document.querySelectorAll('button a[href]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.stopPropagation();
    });
  });

  // Collapsible for hverfi sections
  document.querySelectorAll('button.collapsible').forEach((btn) => {
    btn.addEventListener('click', handleHverfiButtonClick);
  });

  // Collapsible for device sections
  document.querySelectorAll('button.device-collapsible').forEach((btn) => {
    btn.addEventListener('click', handleDeviceButtonClick);
  });

  // Save scrollstate on form submit
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', saveScrollState);
  });

  initializeOpenSectionsBasedOnURL();
  restoreTempSavedScrollState(); // open states must have been restored first
};

// ===========================================================================

main();