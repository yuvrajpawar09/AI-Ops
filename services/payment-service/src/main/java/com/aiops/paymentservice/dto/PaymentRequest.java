package com.aiops.paymentservice.dto;

/** Body of POST /payments, sent by order-service. */
public record PaymentRequest(String orderId, String customerId, double amount) {
}
