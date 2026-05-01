(function () {
    const filterWrap = document.getElementById("categoryFilter");
    const cards = Array.from(document.querySelectorAll(".service-item"));

    if (filterWrap && cards.length) {
        filterWrap.addEventListener("click", (event) => {
            const button = event.target.closest("button[data-filter]");
            if (!button) {
                return;
            }

            filterWrap.querySelectorAll("button[data-filter]").forEach((item) => {
                item.classList.remove("active", "btn-dark");
                item.classList.add("btn-outline-dark");
            });

            button.classList.add("active", "btn-dark");
            button.classList.remove("btn-outline-dark");

            const filter = button.getAttribute("data-filter");
            cards.forEach((card) => {
                if (filter === "all" || card.dataset.category === filter) {
                    card.style.display = "block";
                } else {
                    card.style.display = "none";
                }
            });
        });
    }
})();

(function () {
    const filterWrap = document.getElementById("adminCategoryFilter");
    const items = Array.from(document.querySelectorAll("[data-admin-category-item]"));

    if (!filterWrap || !items.length) {
        return;
    }

    filterWrap.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-filter]");
        if (!button) {
            return;
        }

        filterWrap.querySelectorAll("button[data-filter]").forEach((item) => {
            item.classList.remove("active", "btn-dark");
            item.classList.add("btn-outline-dark");
        });

        button.classList.add("active", "btn-dark");
        button.classList.remove("btn-outline-dark");

        const filter = button.getAttribute("data-filter");
        items.forEach((item) => {
            item.hidden = !(filter === "all" || item.dataset.category === filter);
        });
    });
})();

(function () {
    const tray = document.getElementById("mobileMoreTray");
    const toggleBtn = document.getElementById("mobileMoreToggleBtn");
    const toggleIcon = document.getElementById("mobileMoreToggleIcon");
    const toggleText = document.getElementById("mobileMoreToggleText");

    if (!tray || !toggleBtn) {
        return;
    }

    const links = Array.from(tray.querySelectorAll("a.mobile-more-link"));

    const setOpen = (open) => {
        tray.hidden = !open;
        toggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
        toggleBtn.setAttribute("aria-label", open ? "Close more navigation" : "Open more navigation");
        if (toggleIcon) {
            toggleIcon.textContent = open ? "×" : "+";
        }
        if (toggleText) {
            toggleText.textContent = open ? "Close" : "More";
        }
        document.body.classList.toggle("mobile-more-open", open);
    };

    toggleBtn.addEventListener("click", (event) => {
        event.preventDefault();
        setOpen(tray.hidden);
    });

    document.addEventListener("click", (event) => {
        if (tray.hidden) {
            return;
        }
        const clickedInsideTray = tray.contains(event.target);
        const clickedToggle = toggleBtn.contains(event.target);
        if (!clickedInsideTray && !clickedToggle) {
            setOpen(false);
        }
    });

    links.forEach((link) => {
        link.addEventListener("click", () => setOpen(false));
    });
})();

(function () {
    const searchToggleBtn = document.getElementById("mobileSearchToggleBtn");
    const searchPanel = document.getElementById("mobileSearchPanel");
    const searchInput = document.getElementById("mobileSearchInput");
    const clearBtn = document.getElementById("mobileSearchClearBtn");
    const searchForm = searchPanel ? searchPanel.querySelector("form.mobile-search-form") : null;

    if (!searchToggleBtn || !searchPanel) {
        return;
    }

    const fallbackTarget = document.body.classList.contains("app-shell") ? "/dashboard/" : "/";

    const getReturnTarget = () => {
        try {
            const stored = sessionStorage.getItem("mobile_search_origin");
            if (stored && !stored.includes("/search/")) {
                return stored;
            }
        } catch (error) {
            // Ignore storage errors.
        }
        return fallbackTarget;
    };

    const setOpen = (open) => {
        searchPanel.hidden = !open;
        searchToggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
        searchToggleBtn.setAttribute("aria-label", open ? "Close search" : "Open search");
        document.body.classList.toggle("mobile-search-open", open);
        if (open) {
            try {
                if (!window.location.pathname.includes("/search/")) {
                    sessionStorage.setItem("mobile_search_origin", window.location.href);
                }
            } catch (error) {
                // Ignore storage errors.
            }
        }
        if (open && searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    };

    searchToggleBtn.addEventListener("click", (event) => {
        event.preventDefault();
        setOpen(searchPanel.hidden);
    });

    if (clearBtn && searchInput) {
        clearBtn.addEventListener("click", () => {
            searchInput.value = "";
            window.location.href = getReturnTarget();
        });
    }

    if (searchForm && searchInput) {
        searchForm.addEventListener("submit", (event) => {
            if (!searchInput.value.trim()) {
                event.preventDefault();
                window.location.href = getReturnTarget();
            }
        });
    }

    document.addEventListener("click", (event) => {
        if (searchPanel.hidden) {
            return;
        }
        const clickedInsidePanel = searchPanel.contains(event.target);
        const clickedToggle = searchToggleBtn.contains(event.target);
        if (!clickedInsidePanel && !clickedToggle) {
            setOpen(false);
        }
    });
})();

(function () {
    const panelEl = document.getElementById("appNotifications");
    const markReadBtn = document.getElementById("markAllReadBtn");
    const notifyButtons = Array.from(document.querySelectorAll(".app-notify-btn"));
    const badges = Array.from(document.querySelectorAll("[data-notify-badge]"));
    const notificationItems = Array.from(document.querySelectorAll("[data-notification-item]"));

    if (!notifyButtons.length) {
        return;
    }

    const currentCount = badges.reduce((max, badge) => {
        const count = Number.parseInt(badge.getAttribute("data-notify-count") || "0", 10);
        return Math.max(max, Number.isNaN(count) ? 0 : count);
    }, 0);

    const updateBadgeView = (isRead) => {
        badges.forEach((badge) => {
            if (isRead) {
                badge.style.display = "none";
                badge.classList.remove("pulse", "is-new");
            } else {
                const count = Number.parseInt(badge.getAttribute("data-notify-count") || "0", 10);
                badge.style.display = count > 0 ? "inline-flex" : "none";
                badge.classList.toggle("pulse", count > 0);
            }
        });
        notificationItems.forEach((item) => item.classList.toggle("is-read", isRead));
    };

    updateBadgeView(false);

    try {
        const countKey = "app_notification_count";
        const readKey = "app_notification_read_count";
        const previous = Number.parseInt(localStorage.getItem(countKey) || "0", 10);
        const readCount = Number.parseInt(localStorage.getItem(readKey) || "0", 10);
        if (currentCount > previous) {
            badges.forEach((badge) => badge.classList.add("is-new"));
        }
        localStorage.setItem(countKey, String(currentCount));
        if (readCount >= currentCount && currentCount > 0) {
            updateBadgeView(true);
        }

        if (markReadBtn) {
            markReadBtn.addEventListener("click", () => {
                localStorage.setItem(readKey, String(currentCount));
                updateBadgeView(true);
            });
        }
    } catch (error) {
        // Ignore storage failures in private browsing modes.
    }

    const setNotifyOpenState = (isOpen) => {
        document.body.classList.toggle("notifications-open", isOpen);
        notifyButtons.forEach((button) => {
            button.classList.toggle("is-open", isOpen);
            const icon = button.querySelector(".app-notify-icon");
            if (!icon) {
                return;
            }
            icon.classList.toggle("bi-bell", !isOpen);
            icon.classList.toggle("bi-x-lg", isOpen);
        });
    };

    if (panelEl) {
        panelEl.addEventListener("show.bs.offcanvas", () => setNotifyOpenState(true));
        panelEl.addEventListener("hidden.bs.offcanvas", () => setNotifyOpenState(false));
    }
})();

(function () {
    const deleteBtn = document.getElementById("deleteProfilePhotoBtn");
    const confirmDeleteBtn = document.getElementById("confirmDeleteProfilePhotoBtn");
    const deleteModalEl = document.getElementById("deleteProfilePhotoModal");
    const photoForm = document.getElementById("profilePhotoForm") || document.getElementById("profileForm");
    const removeInput = document.getElementById("removeAvatarInput");
    const avatarInput = document.getElementById("id_avatar");

    if (!deleteBtn || !removeInput) {
        return;
    }

    deleteBtn.addEventListener("click", (event) => {
        event.preventDefault();
        if (deleteModalEl && window.bootstrap) {
            const modal = bootstrap.Modal.getOrCreateInstance(deleteModalEl);
            modal.show();
            return;
        }
        removeInput.value = "1";
        deleteBtn.classList.add("is-armed");
    });

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", () => {
            removeInput.value = "1";
            if (avatarInput) {
                avatarInput.value = "";
            }
            deleteBtn.classList.add("is-armed");

            if (document.activeElement instanceof HTMLElement) {
                document.activeElement.blur();
            }

            if (deleteModalEl && window.bootstrap) {
                const modal = bootstrap.Modal.getOrCreateInstance(deleteModalEl);
                modal.hide();
            }

            if (photoForm) {
                photoForm.submit();
            }
        });
    }

    if (deleteModalEl) {
        deleteModalEl.addEventListener("hidden.bs.modal", () => {
            if (deleteBtn) {
                deleteBtn.focus();
            }
        });
    }

    if (avatarInput) {
        avatarInput.addEventListener("change", () => {
            if (avatarInput.files && avatarInput.files.length > 0) {
                removeInput.value = "0";
                deleteBtn.classList.remove("is-armed");
            }
        });
    }
})();

// Native Mobile App UI Interactivity - Swipe to go back
(function () {
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;

    document.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, {passive: true});

    document.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        handleSwipeGesture();
    }, {passive: true});

    function handleSwipeGesture() {
        const deltaX = touchEndX - touchStartX;
        const deltaY = Math.abs(touchEndY - touchStartY);
        
        // Trigger: Swipe right > 60px, mostly horizontal, originating within 40px of left screen edge
        if (deltaX > 60 && deltaY < Math.abs(deltaX / 2) && touchStartX < 40) {
            
            // Native-like visual feedback: slide page to the right
            document.body.style.transition = 'transform 0.25s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.2s ease';
            document.body.style.transform = `translateX(${deltaX + 100}px)`;
            document.body.style.opacity = '0.3';
            
            setTimeout(() => {
                if (window.history.length > 1 || document.referrer) {
                    window.history.back();
                } else {
                    document.body.style.transform = 'none';
                    document.body.style.opacity = '1';
                }
            }, 200);
        }
    }
})();
