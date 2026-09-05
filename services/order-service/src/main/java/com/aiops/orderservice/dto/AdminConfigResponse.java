package com.aiops.orderservice.dto;

/** Body returned by both GET and POST /admin/config - always the full current state. */
public record AdminConfigResponse(boolean rejectZeroAmount) {
}
