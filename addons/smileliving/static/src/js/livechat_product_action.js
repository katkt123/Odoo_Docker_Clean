/** @odoo-module **/
import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";

const ACTION_ID = "smileliving_livechat_product";
const SL_MARKER_RE = /\[\[SL_PRODUCT:(\d+)\]\]/g;

let slScanTimer = null;
function scheduleScan(rootNode) {
    if (slScanTimer) {
        return;
    }
    slScanTimer = window.setTimeout(() => {
        slScanTimer = null;
        scanAndRenderProductCards(rootNode);
    }, 200);
}

let slPreviewTimer = null;
function schedulePreview(composerRoot) {
    if (slPreviewTimer) {
        return;
    }
    slPreviewTimer = window.setTimeout(() => {
        slPreviewTimer = null;
        ensureInlinePreviewInComposer(composerRoot);
    }, 120);
}

const slState = {
    selectedProducts: [],
    productCache: new Map(),
    isHooked: false,
    hookObserverInstalled: false,
    activeComposerRoot: null,
    activeInputEl: null,
    debug: true,
    hookRetryTimer: null,
    missingHookLogCount: 0,
    threadScanTimer: null,
    threadRescanTimer: null,
    threadRescanAttempts: 0,
    renderedAny: false,
};

function isNodeAttached(node) {
    if (!node) {
        return false;
    }
    const root = node.getRootNode?.();
    if (root?.host) {
        // Inside shadow DOM
        return root.contains(node);
    }
    return document.contains(node);
}

function logDebug(...args) {
    if (slState.debug) {
        // eslint-disable-next-line no-console
        console.log("[SmileLiving]", ...args);
    }
}

function getRoots() {
    const roots = [];
    const livechatRoot = document.querySelector(".o-livechat-root") || document.querySelector(".o_livechat_root") || null;
    if (livechatRoot?.shadowRoot) {
        roots.push(livechatRoot.shadowRoot);
    }
    if (livechatRoot) {
        roots.push(livechatRoot);
    }
    // Look for common iframe host (website livechat widget can be inside an iframe).
    const iframe = document.querySelector("iframe[name='im_livechat']") || document.querySelector("iframe.o_livechat_iframe");
    const iframeDoc = iframe?.contentDocument || null;
    if (iframeDoc) {
        const iframeRoot = iframeDoc.querySelector(".o-livechat-root") || iframeDoc.querySelector(".o_livechat_root") || null;
        if (iframeRoot?.shadowRoot) {
            roots.push(iframeRoot.shadowRoot);
        }
        if (iframeRoot) {
            roots.push(iframeRoot);
        } else {
            roots.push(iframeDoc);
        }
    }
    // Fallback: main document (read-only scanning; safe for thread lookup).
    roots.push(document);
    return roots.filter(Boolean);
}

async function searchProducts(term, limit = 5) {
    const csrfToken = document.querySelector('meta[name="csrf_token"]')?.getAttribute('content');
    const response = await fetch("/smileliving/livechat/search_product", {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify({ term, limit }),
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    // Controller returns a bare list; fall back to raw payload when no wrapper.
    return payload?.result ?? payload ?? [];
}

async function fetchProductInfo(productId) {
    const csrfToken = document.querySelector('meta[name="csrf_token"]')?.getAttribute('content');
    const response = await fetch("/smileliving/livechat/product_info", {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify({ product_id: productId }),
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    // Controller returns a bare dict; fall back to raw payload when no wrapper.
    const data = payload?.result ?? payload ?? null;
    if (data === false) {
        return buildUnavailablePayload(productId);
    }
    return data;
}

async function addProductToCart(productId, quantity = 1) {
    const csrfToken = document.querySelector('meta[name="csrf_token"]')?.getAttribute('content');
    const response = await fetch("/smileliving/livechat/add_to_cart", {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify({ product_id: productId, quantity }),
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (payload?.error) {
        throw new Error(payload.error);
    }
    return payload?.result || payload;
}

function escapeHtml(s) {
    return String(s || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function buildUnavailablePayload(productId) {
    return {
        id: Number(productId),
        variant_id: false,
        name: `Sản phẩm #${productId}`,
        url: "/shop",
        price: 0.0,
        price_display: "Không khả dụng",
        image_url: "/web/static/img/placeholder.png",
        unavailable: true,
    };
}

function buildCardHtml(product, { removable = true } = {}) {
    const name = escapeHtml(product?.name);
    const price = escapeHtml(product?.price_display);
    const url = escapeHtml(product?.url);
    const img = escapeHtml(product?.image_url);
    const close = removable
        ? `<button type="button" class="btn btn-sm btn-link text-muted p-0 ms-2 sl-livechat-product-remove" aria-label="Remove" title="Remove">×</button>`
        : "";
    return `
        <div class="d-flex align-items-start gap-2 border rounded p-2 bg-white sl-livechat-product-card" style="max-width: 100%;">
            <img src="${img}" alt="${name}" class="rounded" style="width: 48px; height: 48px; object-fit: cover;" />
            <div class="d-flex flex-column flex-grow-1 overflow-hidden">
                <div class="fw-semibold text-truncate" title="${name}">${name}</div>
                <div class="text-muted small">${price}</div>
                <a class="small text-truncate" href="${url}" target="_blank" rel="noopener">${url}</a>
            </div>
            ${close}
        </div>
    `;
}

function buildFallbackCardHtml(productId, { removable = true } = {}) {
    const close = removable
        ? `<button type="button" class="btn btn-sm btn-link text-muted p-0 ms-2 sl-livechat-product-remove" aria-label="Remove" title="Remove">×</button>`
        : "";
    return `
        <div class="d-flex align-items-start gap-2 border rounded p-2 bg-white sl-livechat-product-card" style="max-width: 100%;">
            <div class="rounded bg-secondary-subtle d-flex align-items-center justify-content-center" style="width: 48px; height: 48px;">
                <span class="small text-muted">#${productId}</span>
            </div>
            <div class="d-flex flex-column flex-grow-1 overflow-hidden">
                <div class="fw-semibold text-truncate" title="Sản phẩm #${productId}">Sản phẩm #${productId}</div>
                <div class="text-muted small">Thông tin sản phẩm hiện không khả dụng</div>
            </div>
            ${close}
        </div>
    `;
}

function findLivechatRoot() {
    const livechatRoot = document.querySelector(".o-livechat-root") || document.querySelector(".o_livechat_root");
    if (livechatRoot) {
        return livechatRoot;
    }
    const iframe = document.querySelector("iframe[name='im_livechat']") || document.querySelector("iframe.o_livechat_iframe");
    const iframeDoc = iframe?.contentDocument || null;
    if (!iframeDoc) {
        return null;
    }
    return iframeDoc.querySelector(".o-livechat-root") || iframeDoc.querySelector(".o_livechat_root") || iframeDoc;
}

function getLivechatShadowRoot() {
    const rootEl = document.querySelector(".o-livechat-root") || document.querySelector(".o_livechat_root");
    return rootEl?.shadowRoot || null;
}

function getDomSearchRoot() {
    // Prefer shadow root if present; else document.
    return getLivechatShadowRoot() || document;
}

function getQueryRoots(livechatRoot) {
    const roots = [];
    if (livechatRoot?.shadowRoot) {
        roots.push(livechatRoot.shadowRoot);
    }
    if (livechatRoot) {
        roots.push(livechatRoot);
    }
    return roots;
}

function getDeepActiveElement() {
    // Support focus inside open shadow roots.
    const livechatShadow = getLivechatShadowRoot();
    if (livechatShadow?.activeElement) {
        return livechatShadow.activeElement;
    }
    let active = document.activeElement;
    while (active?.shadowRoot?.activeElement) {
        active = active.shadowRoot.activeElement;
    }
    return active;
}

function findComposerRoot(livechatRoot) {
    const roots = getQueryRoots(livechatRoot || findLivechatRoot());
    for (const root of roots) {
        const found =
            root.querySelector?.(".o-mail-Composer") ||
            root.querySelector?.(".o-mail-Composer-core") ||
            root.querySelector?.(".o-livechat-Composer") ||
            root.querySelector?.("form.o-mail-Composer") ||
            root.querySelector?.(".o_composer_form") ||
            null;
        if (found) {
            return found;
        }
    }
    return null;
}

function findComposerRootFromInput(inputEl) {
    if (!inputEl) {
        return null;
    }
    return (
        inputEl.closest?.(".o-mail-Composer") ||
        inputEl.closest?.("form") ||
        inputEl.closest?.(".o-livechat-root") ||
        inputEl.closest?.(".o_livechat_root") ||
        inputEl.parentElement ||
        null
    );
}

function resolveActiveInputEl() {
    const active = getDeepActiveElement();
    if (active && (active.tagName === "TEXTAREA" || active.tagName === "INPUT" || active.isContentEditable)) {
        return active;
    }
    // Don't pass the livechat host element here; queries don't pierce shadow DOM.
    return slState.activeInputEl || findAnyComposerInput();
}

function findComposerRootFromOwner(owner) {
    // Try to anchor to the composer of the clicked action.
    const btn = document.querySelector("button[name='smileliving_livechat_product']");
    const fromBtn = btn?.closest?.(".o-mail-Composer") || null;
    const fromOwner = owner?.el?.closest?.(".o-mail-Composer") || owner?.rootRef?.el?.closest?.(".o-mail-Composer") || null;
    if (fromOwner) {
        return fromOwner;
    }
    if (fromBtn) {
        return fromBtn;
    }
    const roots = getQueryRoots(findLivechatRoot());
    for (const root of roots) {
        const found =
            root.querySelector?.(".o-mail-Composer") ||
            root.querySelector?.(".o-mail-Composer-core") ||
            root.querySelector?.(".o-livechat-Composer") ||
            root.querySelector?.("form.o-mail-Composer") ||
            root.querySelector?.(".o_composer_form") ||
            null;
        if (found) {
            return found;
        }
    }
    return document.querySelector(".o-mail-Composer");
}

function findComposerInput(composerRoot) {
    return (
        composerRoot?.querySelector("textarea") ||
        composerRoot?.querySelector(".o-mail-Composer-input") ||
        composerRoot?.querySelector('[contenteditable="true"]') ||
        null
    );
}

function findAnyComposerInput(livechatRoot) {
    const roots = getQueryRoots(livechatRoot || findLivechatRoot());
    for (const root of roots) {
        const candidates = Array.from(
            root.querySelectorAll?.("textarea.o-mail-Composer-input, textarea, [contenteditable='true'], input") || []
        );
        const visible = candidates.find((el) => {
            const style = window.getComputedStyle(el);
            return style.display !== "none" && style.visibility !== "hidden" && el.offsetParent !== null;
        });
        if (visible) {
            return visible;
        }
        if (candidates.length) {
            return candidates[0];
        }
    }
    return null;
}

function findSendButton(composerRoot) {
    return (
        composerRoot?.querySelector("button.o-mail-Composer-send") ||
        composerRoot?.querySelector("button[aria-label='Send']") ||
        composerRoot?.querySelector("button[name='send-message']") ||
        composerRoot?.querySelector("button[type='submit']") ||
        null
    );
}

function setInputValue(inputEl, value) {
    if (!inputEl) {
        return;
    }
    if (inputEl.tagName === "TEXTAREA" || inputEl.tagName === "INPUT") {
        inputEl.value = value;
        inputEl.dispatchEvent(new Event("input", { bubbles: true }));
        return;
    }
    if (inputEl.isContentEditable) {
        inputEl.textContent = value;
        inputEl.dispatchEvent(new Event("input", { bubbles: true }));
    }
}

function getInputValue(inputEl) {
    if (!inputEl) {
        return "";
    }
    if (inputEl.tagName === "TEXTAREA" || inputEl.tagName === "INPUT") {
        return inputEl.value || "";
    }
    if (inputEl.isContentEditable) {
        return inputEl.textContent || "";
    }
    return "";
}

function buildInlinePreviewHtml(products) {
    if (!products?.length) {
        return "";
    }
    const rows = products
        .map((product) => {
            const name = escapeHtml(product?.name);
            const price = escapeHtml(product?.price_display);
            const img = escapeHtml(product?.image_url);
            return `
                <div class="d-flex align-items-center gap-2 border rounded px-2 py-1 bg-white sl-livechat-preview-row" style="max-width: 100%;">
                    <img src="${img}" alt="${name}" class="rounded" style="width: 28px; height: 28px; object-fit: cover;" />
                    <div class="d-flex flex-column flex-grow-1 overflow-hidden">
                        <div class="fw-semibold text-truncate" style="font-size: 12px; line-height: 1.2;" title="${name}">${name}</div>
                        <div class="text-muted text-truncate" style="font-size: 11px; line-height: 1.2;">${price}</div>
                    </div>
                    <button type="button" class="btn btn-sm btn-link text-muted p-0 sl-livechat-product-remove" data-product-id="${product.id}" aria-label="Remove" title="Remove">×</button>
                </div>`;
        })
        .join("");
    return `<div class="d-flex flex-column gap-1">${rows}</div>`;
}

function getInlinePreviewNode(composerRoot) {
    return composerRoot?.querySelector(".sl-livechat-inline-preview") || null;
}

function getInlinePreviewNodeFromHost(hostEl) {
    return hostEl?.querySelector?.(".sl-livechat-inline-preview") || null;
}

function resolvePreviewHostAndInsertBefore(inputEl, composerRoot) {
    // Many livechat UIs wrap the textarea in a fixed-height bubble. We'll anchor the preview
    // to the textarea container using absolute positioning and enable overflow visibility.
    const inputContainer = inputEl?.parentElement || null;
    const outerHost = inputContainer?.parentElement || composerRoot || inputEl?.getRootNode?.() || null;
    return { inputContainer, outerHost };
}

function ensureInlinePreviewInComposer(composerRootParam) {
    let inputEl = resolveActiveInputEl();
    if (!inputEl) {
        inputEl = findAnyComposerInput(findLivechatRoot());
    }
    const derivedComposerRoot = findComposerRootFromInput(inputEl);
    const composerRoot =
        composerRootParam ||
        slState.activeComposerRoot ||
        derivedComposerRoot ||
        findComposerRoot(findLivechatRoot()) ||
        document.querySelector(".o-mail-Composer") ||
        null;

    if (!inputEl || !composerRoot) {
        return;
    }

    if (inputEl) {
        slState.activeInputEl = inputEl;
    }
    if (composerRoot) {
        slState.activeComposerRoot = composerRoot;
    }

    const { inputContainer, outerHost } = resolvePreviewHostAndInsertBefore(inputEl, composerRoot);
    const hostEl = inputContainer || outerHost || composerRoot || document.body;
    if (!hostEl) {
        return;
    }

    let node = getInlinePreviewNodeFromHost(hostEl);
    if (!slState.selectedProducts.length) {
        node?.remove();
        return;
    }

    if (!node) {
        node = document.createElement("div");
        node.className = "sl-livechat-inline-preview mb-1";
        // Ensure visibility even if surrounding layout is complex.
        node.style.display = "block";
        node.style.zIndex = "9999";
        // Avoid blocking clicks to the send button; child buttons will re-enable pointer events.
        node.style.pointerEvents = "none";

        if (inputContainer) {
            // Make the input container a positioning context and allow content to overflow.
            inputContainer.style.position = inputContainer.style.position || "relative";
            inputContainer.style.overflow = "visible";
            // Some themes clip at the parent level too.
            if (inputContainer.parentElement) {
                inputContainer.parentElement.style.overflow = "visible";
            }

            node.style.position = "absolute";
            node.style.left = "0";
            node.style.right = "0";
            node.style.bottom = "calc(100% + 6px)";

            inputContainer.appendChild(node);
        } else {
            // Fallback: regular flow insertion
            node.style.position = "relative";
            hostEl.appendChild(node);
        }
    }
    node.innerHTML = buildInlinePreviewHtml(slState.selectedProducts);
    node.querySelectorAll(".sl-livechat-product-remove").forEach((btn) => {
        btn.style.pointerEvents = "auto";
        const pid = Number(btn.dataset.productId || 0);
        btn.addEventListener("click", () => {
            removeSelectedProduct(pid, { alsoStripFromInput: true });
        });
    });
}

function clearSelectedProducts() {
    slState.selectedProducts = [];
    ensureInlinePreviewInComposer(slState.activeComposerRoot);
}

function removeSelectedProduct(productId, { alsoStripFromInput = true } = {}) {
    slState.selectedProducts = slState.selectedProducts.filter((p) => p.id !== productId);
    if (alsoStripFromInput) {
        const livechat = findLivechatRoot();
        const inputEl = resolveActiveInputEl() || findAnyComposerInput(livechat);
        if (inputEl) {
            const current = getInputValue(inputEl);
            const marker = `[[SL_PRODUCT:${productId}]]`;
            // Remove marker occurrences and trim surrounding blank lines.
            const next = current
                .split(/\n+/)
                .filter((line) => line.trim() !== marker)
                .join("\n");
            setInputValue(inputEl, next);
        }
    }
    ensureInlinePreviewInComposer(slState.activeComposerRoot);
}

function showPreview(owner, product) {
    if (!product) {
        return;
    }
    // Tránh trùng sản phẩm trong danh sách
    const exists = slState.selectedProducts.some((p) => p.id === product.id);
    if (!exists) {
        slState.selectedProducts.push(product);
    }
    slState.productCache.set(product.id, product);
    const inputEl = resolveActiveInputEl() || findAnyComposerInput(findLivechatRoot());
    slState.activeInputEl = inputEl;
    const composerRoot = findComposerRootFromInput(inputEl) || findComposerRootFromOwner(owner) || findComposerRoot(findLivechatRoot());
    slState.activeComposerRoot = composerRoot;
    ensureInlinePreviewInComposer(composerRoot);
    if (composerRoot) {
        schedulePreview(composerRoot);
    }

    // eslint-disable-next-line no-console
    console.log("[SmileLiving] preview ensured", { product });
}

function getThreadRoot() {
    const roots = getRoots();
    for (const root of roots) {
        const found =
            root.querySelector?.(".o-mail-Thread") ||
            root.querySelector?.(".o-mail-ThreadView") ||
            root.querySelector?.(".o-mail-MessageList") ||
            root.querySelector?.(".o-mail-MessageListView") ||
            null;
        if (found) {
            return found;
        }
    }
    // Fallback: try the main document in case the livechat DOM isn't under our known roots.
    return (
        document.querySelector(".o-mail-Thread, .o-mail-ThreadView, .o-mail-MessageList, .o-mail-MessageListView") ||
        null
    );
}

function ensureThreadScanLoop() {
    if (slState.threadScanTimer) {
        return;
    }
    // Poll for the thread root to appear (e.g., after page reload) and scan markers to cards.
    slState.threadScanTimer = window.setInterval(() => {
        if (slState.renderedAny) {
            window.clearInterval(slState.threadScanTimer);
            slState.threadScanTimer = null;
            return;
        }
        const threadRoot = getThreadRoot();
        if (!threadRoot) {
            return;
        }
        scheduleScan(threadRoot);
    }, 1000);
}

function kickThreadRescanBurst() {
    if (slState.threadRescanTimer) {
        return;
    }
    slState.threadRescanAttempts = 0;
    slState.threadRescanTimer = window.setInterval(() => {
        if (slState.renderedAny) {
            window.clearInterval(slState.threadRescanTimer);
            slState.threadRescanTimer = null;
            return;
        }
        const threadRoot = getThreadRoot();
        if (threadRoot) {
            scanAndRenderProductCards(threadRoot);
        }
        slState.threadRescanAttempts += 1;
        if (slState.threadRescanAttempts >= 30) {
            window.clearInterval(slState.threadRescanTimer);
            slState.threadRescanTimer = null;
        }
    }, 700);
}

function findMessageBodyNode(messageNode) {
    return (
        messageNode.querySelector(".o-mail-Message-body") ||
        messageNode.querySelector(".o-mail-Message-content") ||
        messageNode.querySelector(".o-mail-Message-text") ||
        messageNode.querySelector(".o_Message_content") ||
        messageNode.querySelector(".o_Message_body") ||
        messageNode.querySelector(".o_MessageView_body") ||
        messageNode.querySelector(".o_MessageView_content") ||
        messageNode.querySelector("p") ||
        messageNode
    );
}

async function renderMessageProducts(messageNode, productIds) {
    if (!messageNode || !productIds?.length) {
        return;
    }
    const uniqueIds = [...new Set(productIds.map((x) => parseInt(x, 10)).filter(Boolean))];
    const products = [];
    for (const pid of uniqueIds) {
        let product = slState.productCache.get(pid);
        if (!product) {
            try {
                // eslint-disable-next-line no-await-in-loop
                product = await fetchProductInfo(pid);
            } catch (err) {
                logDebug("fetchProductInfo failed", { pid, err });
            }
            if (product) {
                slState.productCache.set(pid, product);
            }
        }
        if (product) {
            products.push(product);
        }
    }
    const bodyNode = findMessageBodyNode(messageNode);
    // Preserve user text even if marker shares the same line (strip tokens, keep rest).
    const originalText = (bodyNode?.textContent || "")
        .replace(SL_MARKER_RE, "")
        .replace(/\n{2,}/g, "\n")
        .trim();

    if (!products.length) {
        // Fallback: render placeholder cards so we stop rescan loops when product info is unavailable.
        const cardsHtml = uniqueIds
            .map((pid) => buildFallbackCardHtml(pid, { removable: true }))
            .join("");
        bodyNode.innerHTML = `${originalText ? `<div class="mb-2">${escapeHtml(originalText)}</div>` : ""}${cardsHtml}`;
        bodyNode.querySelectorAll(".sl-livechat-product-remove").forEach((btn) => {
            btn.addEventListener("click", () => {
                btn.closest?.(".sl-livechat-product-card")?.remove();
            });
        });
        messageNode.dataset.slProductRendered = uniqueIds.join(",");
        slState.renderedAny = true;
        return;
    }

    const cardsHtml = products
        .map((p) => {
            if (p.unavailable) {
                return buildFallbackCardHtml(p.id, { removable: true });
            }
            return buildCardHtml(p, { removable: true });
        })
        .join("");

    bodyNode.innerHTML = `${originalText ? `<div class="mb-2">${escapeHtml(originalText)}</div>` : ""}${cardsHtml}`;

    // Allow removing a single card from the message without deleting the entire message.
    bodyNode.querySelectorAll(".sl-livechat-product-remove").forEach((btn) => {
        btn.addEventListener("click", () => {
            btn.closest?.(".sl-livechat-product-card")?.remove();
        });
    });
    messageNode.dataset.slProductRendered = uniqueIds.join(",");
    slState.renderedAny = true;
}

async function scanAndRenderProductCards(rootNode) {
    const threadRoot = rootNode || getThreadRoot();
    if (!threadRoot) {
        return;
    }

    // IMPORTANT: keep this selector narrow. Scanning every div/li in a livechat thread can freeze the browser.
    let candidates = threadRoot.querySelectorAll(
        ".o-mail-Message, .o_Message, .o_MessageView_message, .o_MessageList_message, .o_Message_content"
    );
    if (!candidates.length) {
        candidates = threadRoot.querySelectorAll(
            ".o-mail-Message-content, .o-mail-Message-body, .o-mail-Message-text, .o_Message_body, .o_Message_content"
        );
    }
    logDebug("scan thread", { root: threadRoot, candidateCount: candidates.length });
    for (const node of candidates) {
        const text = node.textContent || "";
        if (node.dataset?.slProductRendered && !SL_MARKER_RE.test(text)) {
            continue;
        }
        const matches = [...text.matchAll(SL_MARKER_RE)].map((m) => m[1]);
        if (matches.length) {
            logDebug("render markers", { node, matches });
        }
        if (!matches.length) {
            continue;
        }
        const messageNode = node.closest(".o-mail-Message") || node;
        // Mark as processed up front to avoid repeated scans if rendering fails.
        messageNode.dataset.slProductRendered = matches.join(",");
        // eslint-disable-next-line no-await-in-loop
        await renderMessageProducts(messageNode, matches);
    }
}

function ensureHooksInstalled() {
    if (slState.isHooked && isNodeAttached(slState.activeComposerRoot)) {
        return;
    }
    // Composer was destroyed or not yet hooked; reset and try again.
    slState.isHooked = false;
    slState.missingHookLogCount = 0;
    ensureThreadScanLoop();
    kickThreadRescanBurst();

    if (!slState.hookObserverInstalled) {
        slState.hookObserverInstalled = true;
    }

    const tryHook = () => {
        const livechatRoot = findLivechatRoot();
        const inputEl = findAnyComposerInput(livechatRoot);
        const composerRoot = findComposerRootFromInput(inputEl) || findComposerRoot(livechatRoot);
        if (!composerRoot || !inputEl) {
            // Avoid spamming logs while waiting for livechat UI to mount.
            if (slState.missingHookLogCount < 3) {
                logDebug("tryHook: composer or input missing", { composerRoot, inputEl, livechatRoot });
                slState.missingHookLogCount += 1;
            }
            return false;
        }

        logDebug("hooked", { composerRoot, inputEl });

        slState.isHooked = true;
        slState.activeComposerRoot = composerRoot;
        slState.activeInputEl = inputEl;

        const threadRoot = getThreadRoot();

        // Intercept "send" clicks (button can be dynamically rendered).
        composerRoot.addEventListener(
            "click",
            (ev) => {
                const target = ev.target;
                const btn = target?.closest?.("button");
                if (!btn) {
                    return;
                }
                const isSend =
                    btn.matches("button.o-mail-Composer-send") ||
                    btn.matches("button[name='send-message']") ||
                    btn.matches("button[type='submit']") ||
                    btn.getAttribute("aria-label") === "Send";
                if (!isSend) {
                    return;
                }
                if (!slState.selectedProducts.length) {
                    return;
                }
                const livechat = findLivechatRoot();
                const freshInput = resolveActiveInputEl() || findAnyComposerInput(livechat) || inputEl;
                const markers = slState.selectedProducts.map((p) => `[[SL_PRODUCT:${p.id}]]`).join("\n");
                const current = getInputValue(freshInput);
                const next = current ? `${current}\n${markers}` : markers;
                logDebug("inject markers on send", { markers, input: freshInput });
                setInputValue(freshInput, next);

                window.setTimeout(() => {
                    // Clear composer text so markers are not left visible after send.
                    const livechatEl = findLivechatRoot();
                    const resetInput = resolveActiveInputEl() || findAnyComposerInput(livechatEl) || freshInput;
                    setInputValue(resetInput, "");
                    clearSelectedProducts();
                    if (threadRoot) {
                        scanAndRenderProductCards(threadRoot);
                    }
                }, 50);
            },
            true
        );

        // Some livechat UIs send on Enter; inject marker there too.
        inputEl.addEventListener(
            "keydown",
            (ev) => {
                if (ev.key !== "Enter" || ev.shiftKey || ev.ctrlKey || ev.altKey || ev.metaKey) {
                    return;
                }
                if (!slState.selectedProducts.length) {
                    return;
                }
                const livechat = findLivechatRoot();
                const freshInput = resolveActiveInputEl() || findAnyComposerInput(livechat) || inputEl;
                const markers = slState.selectedProducts.map((p) => `[[SL_PRODUCT:${p.id}]]`).join("\n");
                const current = getInputValue(freshInput);
                const next = current ? `${current}\n${markers}` : markers;
                logDebug("inject markers on enter", { markers, input: freshInput });
                setInputValue(freshInput, next);

                // Clear after send fires to avoid leaving markers in the composer.
                window.setTimeout(() => {
                    const livechatEl = findLivechatRoot();
                    const resetInput = resolveActiveInputEl() || findAnyComposerInput(livechatEl) || freshInput;
                    setInputValue(resetInput, "");
                    clearSelectedProducts();
                    const threadRoot = getThreadRoot();
                    if (threadRoot) {
                        scanAndRenderProductCards(threadRoot);
                    }
                }, 60);
            },
            true
        );

        // Observe new messages and convert marker -> card (if thread exists now).
        if (threadRoot) {
            const mo = new MutationObserver(() => {
                scheduleScan(threadRoot);
            });
            mo.observe(threadRoot, { childList: true, subtree: true });
            scheduleScan(threadRoot);
        }

        // Keep inline preview alive across OWL rerenders.
        const moPreview = new MutationObserver(() => {
            schedulePreview(composerRoot);
        });
        moPreview.observe(composerRoot, { childList: true, subtree: true });
        schedulePreview(composerRoot);

        return true;
    };

    if (tryHook()) {
        ensureThreadScanLoop();
        kickThreadRescanBurst();
        return;
    }

    // Poll retry in case no mutation happens but livechat mounts later (e.g., delayed load).
    if (!slState.hookRetryTimer) {
        slState.hookRetryTimer = window.setInterval(() => {
            if (slState.isHooked && isNodeAttached(slState.activeComposerRoot)) {
                window.clearInterval(slState.hookRetryTimer);
                slState.hookRetryTimer = null;
                return;
            }
            tryHook();
        }, 800);
    }

    let shadowObserver;
    const rootObserver = new MutationObserver(() => {
        // If current hook died (composer replaced), clear flag to allow rehooking.
        if (slState.isHooked && !isNodeAttached(slState.activeComposerRoot)) {
            slState.isHooked = false;
        }
        if (slState.isHooked) {
            return;
        }

        const livechatRoot = document.querySelector(".o-livechat-root");
        const shadow = livechatRoot?.shadowRoot;
        if (shadow && !shadowObserver) {
            shadowObserver = new MutationObserver(() => {
                if (slState.isHooked && isNodeAttached(slState.activeComposerRoot)) {
                    return;
                }
                tryHook();
            });
            shadowObserver.observe(shadow, { childList: true, subtree: true });
        }

        tryHook();
    });

    const observeRoot = document.body || document.documentElement;
    if (!observeRoot) {
        document.addEventListener(
            "DOMContentLoaded",
            () => {
                ensureHooksInstalled();
            },
            { once: true }
        );
        return;
    }

    rootObserver.observe(observeRoot, { childList: true, subtree: true });
}

registerComposerAction(ACTION_ID, {
    condition: ({ composer }) => composer.thread?.channel_type === "livechat",
    icon: "fa fa-home",
    name: _t("Chèn sản phẩm"),
    sequenceQuick: 15,
    async onSelected({ owner }) {
        ensureHooksInstalled();
        slState.activeComposerRoot = findComposerRootFromOwner(owner);
        const term = window.prompt(_t("Nhập từ khóa sản phẩm để chèn"));
        if (!term) {
            return;
        }
        try {
            // eslint-disable-next-line no-console
            console.log("[SmileLiving] searching products", { term });
            const results = await searchProducts(term, 5);
            if (!results || !results.length) {
                const notify = owner?.env?.services?.notification;
                notify?.add(_t("Không tìm thấy sản phẩm."), { type: "warning" }) || window.alert(_t("Không tìm thấy sản phẩm."));
                return;
            }
            const product = results[0];
            showPreview(owner, product);
        } catch (err) {
            // eslint-disable-next-line no-console
            console.error("SmileLiving livechat product search failed", err);
            const notify = owner?.env?.services?.notification;
            notify?.add(_t("Lỗi khi tìm sản phẩm."), { type: "danger" }) || window.alert(_t("Lỗi khi tìm sản phẩm."));
        }
    },
});

// Install hooks early for the website livechat widget.
if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        () => {
            ensureHooksInstalled();
            ensureThreadScanLoop();
            kickThreadRescanBurst();
            // Try an eager scan on load so markers in history render even before hooks latch.
            scheduleScan(document);
            window.setTimeout(() => scheduleScan(document), 400);
            window.setTimeout(() => scheduleScan(document), 1100);
        },
        { once: true }
    );
} else {
    ensureHooksInstalled();
    ensureThreadScanLoop();
    kickThreadRescanBurst();
    scheduleScan(document);
    window.setTimeout(() => scheduleScan(document), 400);
    window.setTimeout(() => scheduleScan(document), 1100);
}

// Simple debug handle for browser console.
window.SmileLivingLivechat = {
    state: slState,
    ensureHooksInstalled,
    scanAndRenderProductCards,
    getLivechatShadowRoot,
};
