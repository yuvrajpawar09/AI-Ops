package com.aiops.paymentservice.dto;

/** Body returned by POST /payments. status is "SUCCESS" or "FAILED". */
public record PaymentResponse(String paymentId, String orderId, String status) {
}
