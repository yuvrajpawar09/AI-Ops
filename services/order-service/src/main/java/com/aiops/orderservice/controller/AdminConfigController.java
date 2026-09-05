package com.aiops.orderservice.controller;

import com.aiops.orderservice.config.RuntimeConfig;
import com.aiops.orderservice.dto.AdminConfigRequest;
import com.aiops.orderservice.dto.AdminConfigResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Phase 6: the "actuation" surface auto-remediation acts on. Deliberately
 * tiny and unauthenticated - this is a college demo running entirely on
 * localhost, not a production admin API. A real system would put an auth
 * boundary and an audit trail here; rca-agent's own remediationLog is this
 * project's stand-in for that audit trail, kept on the caller's side.
 */
@RestController
@RequestMapping("/admin/config")
public class AdminConfigController {

    private static final Logger log = LoggerFactory.getLogger(AdminConfigController.class);

    private final RuntimeConfig runtimeConfig;

    public AdminConfigController(RuntimeConfig runtimeConfig) {
        this.runtimeConfig = runtimeConfig;
    }

    @GetMapping
    public ResponseEntity<AdminConfigResponse> getConfig() {
        return ResponseEntity.ok(new AdminConfigResponse(runtimeConfig.isRejectZeroAmount()));
    }

    @PostMapping
    public ResponseEntity<AdminConfigResponse> updateConfig(@RequestBody AdminConfigRequest request) {
        if (request.rejectZeroAmount() != null) {
            runtimeConfig.setRejectZeroAmount(request.rejectZeroAmount());
            log.warn("Runtime config changed via /admin/config: rejectZeroAmount={}", request.rejectZeroAmount());
        }
        return ResponseEntity.ok(new AdminConfigResponse(runtimeConfig.isRejectZeroAmount()));
    }
}
