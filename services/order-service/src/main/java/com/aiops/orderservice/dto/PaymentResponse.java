package com.aiops.orderservice.dto;

/** What payment-service's POST /payments replies with. status is "SUCCESS" or "FAILED". */
public record PaymentResponse(String paymentId, String orderId, String status) {
}
