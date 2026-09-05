package com.aiops.orderservice.dto;

/** Body of POST /admin/config. Null means "leave that flag unchanged" - not used yet with a single flag, but keeps the endpoint extensible without a breaking change. */
public record AdminConfigRequest(Boolean rejectZeroAmount) {
}
