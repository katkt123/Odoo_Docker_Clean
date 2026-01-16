/** @odoo-module **/
import { Component, useState, mount, xml } from "@odoo/owl";

class LoanCalculator extends Component {
    static template = xml`
        <div class="sl-loan-calculator shadow-sm rounded-3 bg-white p-4">
            <p class="text-muted small mb-3" id="sl-loan-policy-debug">Debug: waiting for loan calculator...</p>
            <div class="row g-4">
                <div class="col-lg-6">
                    <h2 class="h5 mb-4">Nhập thông tin</h2>
                    <div class="sl-field mb-3">
                        <label class="form-label">Giá trị nhà đất (tỷ VND)</label>
                        <div class="d-flex align-items-center gap-3">
                            <input
                                type="range"
                                min="1"
                                max="30"
                                step="0.5"
                                data-field="propertyValue"
                                t-att-value="state.propertyValue"
                                t-on-input="onFieldChange"
                                class="form-range"
                            />
                            <div class="flex-grow-1">
                                <input
                                    type="number"
                                    min="1"
                                    step="0.1"
                                    class="form-control"
                                    data-field="propertyValue"
                                    t-att-value="state.propertyValue"
                                    t-on-change="onFieldChange"
                                />
                            </div>
                        </div>
                    </div>

                    <div class="sl-field mb-3">
                        <label class="form-label">Tỷ lệ vay (%)</label>
                        <div class="d-flex align-items-center gap-3">
                            <input
                                type="range"
                                min="30"
                                max="90"
                                step="5"
                                class="form-range"
                                data-field="loanRatio"
                                t-att-value="state.loanRatio"
                                t-on-input="onFieldChange"
                            />
                            <div style="width: 120px;" class="flex-shrink-0">
                                <div class="input-group">
                                    <input
                                        type="number"
                                        min="0"
                                        max="100"
                                        step="1"
                                        class="form-control"
                                        data-field="loanRatio"
                                        t-att-value="state.loanRatio"
                                        t-on-change="onFieldChange"
                                    />
                                    <span class="input-group-text">%</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="sl-field mb-3">
                        <label class="form-label">Thời hạn vay (năm)</label>
                        <input
                            type="number"
                            min="1"
                            max="30"
                            class="form-control"
                            data-field="years"
                            t-att-value="state.years"
                            t-on-change="onFieldChange"
                        />
                    </div>

                    <div class="sl-field mb-3">
                        <label class="form-label">Lãi suất %/năm</label>
                        <input
                            type="number"
                            min="0"
                            step="0.1"
                            class="form-control"
                            data-field="rate"
                            t-att-value="state.rate"
                            t-on-change="onFieldChange"
                        />
                    </div>

                    <div class="sl-field">
                        <label class="form-label d-block">Phương thức trả</label>
                        <div class="form-check form-check-inline">
                            <input
                                class="form-check-input"
                                type="radio"
                                name="loan_method"
                                data-field="method"
                                value="decreasing"
                                t-att-checked="state.method === 'decreasing'"
                                t-on-change="onFieldChange"
                            />
                            <label class="form-check-label">Dư nợ giảm dần</label>
                        </div>
                        <div class="form-check form-check-inline">
                            <input
                                class="form-check-input"
                                type="radio"
                                name="loan_method"
                                data-field="method"
                                value="equal"
                                t-att-checked="state.method === 'equal'"
                                t-on-change="onFieldChange"
                            />
                            <label class="form-check-label">Đều hàng tháng</label>
                        </div>
                    </div>
                </div>

                <div class="col-lg-6">
                    <div class="sl-summary p-4 border rounded-3 bg-light">
                        <h2 class="h5">Kết quả</h2>
                        <div class="mt-3">
                            <div class="d-flex justify-content-between">
                                <span>Tiền vay</span>
                                <strong class="text-primary"><t t-esc="formatCurrency(loanAmount)"/></strong>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span>Tiền trả trước</span>
                                <strong class="text-muted"><t t-esc="formatCurrency(downPayment)"/></strong>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span>Thanh toán tháng đầu</span>
                                <strong class="text-danger"><t t-esc="formatCurrency(firstPayment)"/></strong>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span>Lãi cần trả</span>
                                <strong class="text-warning"><t t-esc="formatCurrency(totalInterest)"/></strong>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span>Tổng phải trả</span>
                                <strong class="text-success"><t t-esc="formatCurrency(totalRepayment)"/></strong>
                            </div>
                        </div>
                        <div class="mt-4">
                            <button type="button" class="btn btn-primary w-100">Yêu cầu tư vấn</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    setup() {
        this.state = useState({
            propertyValue: 6,
            loanRatio: 70,
            years: 10,
            rate: 8,
            method: "decreasing",
        });
    }

    onFieldChange(ev) {
        const field = ev.target.dataset.field;
        if (!field) {
            return;
        }
        const raw = ev.target.value;
        if (field === "method") {
            this.state.method = raw;
            return;
        }
        const parsed = Number(raw);
        this.state[field] = Number.isNaN(parsed) ? 0 : parsed;
    }

    get loanValue() {
        return Math.max(0, (this.state.propertyValue || 0) * 1_000_000_000);
    }

    get loanAmount() {
        return Math.max(0, this.loanValue * ((this.state.loanRatio || 0) / 100));
    }

    get loanMonths() {
        return Math.max(1, (this.state.years || 0) * 12);
    }

    get monthlyRate() {
        return (this.state.rate || 0) / 100 / 12;
    }

    get downPayment() {
        return Math.max(0, this.loanValue - this.loanAmount);
    }

    get totalInterest() {
        if (!this.loanAmount) {
            return 0;
        }
        if (this.state.method === "equal") {
            const months = this.loanMonths;
            const rate = this.monthlyRate;
            if (!rate) {
                return 0;
            }
            const factor = Math.pow(1 + rate, months);
            const monthly = (this.loanAmount * rate * factor) / (factor - 1);
            return Math.max(0, monthly * months - this.loanAmount);
        }
        const months = this.loanMonths;
        const rate = this.monthlyRate;
        return Math.max(0, (this.loanAmount * rate * months) / 2);
    }

    get firstPayment() {
        if (!this.loanAmount) {
            return 0;
        }
        const months = this.loanMonths;
        if (this.state.method === "equal") {
            const rate = this.monthlyRate;
            if (!rate) {
                return this.loanAmount / months;
            }
            const factor = Math.pow(1 + rate, months);
            return (this.loanAmount * rate * factor) / (factor - 1);
        }
        const principal = this.loanAmount / months;
        return principal + this.loanAmount * this.monthlyRate;
    }

    get totalRepayment() {
        return this.loanAmount + this.totalInterest;
    }

    formatCurrency(value) {
        const rounded = Math.round(value || 0);
        return new Intl.NumberFormat("vi-VN").format(rounded) + " ₫";
    }
}

async function initLoanCalculator(attempt = 0) {
    // eslint-disable-next-line no-console
    console.log("[SmileLiving] loan_calculator module loaded");
    const root = document.getElementById("sl-loan-policy");
    if (!root) {
        console.warn("[SmileLiving] loan policy root missing");
        return;
    }
    if (!(root instanceof HTMLElement)) {
        console.warn("[SmileLiving] loan policy root is not an HTMLElement", {
            nodeType: root.nodeType,
            ctor: root?.constructor?.name,
        });
        return;
    }
    if (!root.isConnected) {
        if (attempt < 30) {
            requestAnimationFrame(() => {
                void initLoanCalculator(attempt + 1);
            });
            return;
        }
        console.warn("[SmileLiving] loan policy root not connected; aborting mount");
        return;
    }
    if (root.dataset.loanStatus === "mounted") {
        return;
    }
    // Make it obvious whether JS runs even before OWL mounts.
    // root.innerHTML = '<div class="text-muted">Debug: JS chạy, đang mount...</div>';
    root.dataset.loanStatus = "mounting";
    try {
        await mount(LoanCalculator, root);
    } catch (err) {
        // eslint-disable-next-line no-console
        console.error("[SmileLiving] loan calculator mount failed", err);
        root.dataset.loanStatus = "mount_failed";
        root.innerHTML = '<div class="alert alert-danger">Loan calculator mount failed. Mở Console để xem lỗi.</div>';
        return;
    }
    root.dataset.loanStatus = "mounted";
    // const debugEl = document.getElementById("sl-loan-policy-debug");
    // if (debugEl) {
    //     debugEl.textContent = "Debug: loan calculator mounted";
    // }
}

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        () => {
            void initLoanCalculator();
        },
        { once: true }
    );
} else {
    void initLoanCalculator();
}

export { LoanCalculator };
