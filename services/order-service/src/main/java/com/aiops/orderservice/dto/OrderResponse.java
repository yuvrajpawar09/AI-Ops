package com.aiops.orderservice.dto;

/** Body returned by POST /orders. */
public record OrderResponse(String orderId, String traceId, String status, String message) {
}
