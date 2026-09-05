package com.aiops.orderservice.config;

import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Phase 6: in-memory, runtime-toggleable flags. There's exactly one flag
 * today (rejectZeroAmount), flipped via POST /admin/config - either by hand
 * or by rca-agent's auto-remediation. AtomicBoolean rather than a plain
 * field because the flag is read on every order-placing request thread and
 * written from whichever thread handles the admin POST.
 */
@Component
public class RuntimeConfig {

    private final AtomicBoolean rejectZeroAmount = new AtomicBoolean(false);

    public boolean isRejectZeroAmount() {
        return rejectZeroAmount.get();
    }

    public void setRejectZeroAmount(boolean value) {
        rejectZeroAmount.set(value);
    }
}
