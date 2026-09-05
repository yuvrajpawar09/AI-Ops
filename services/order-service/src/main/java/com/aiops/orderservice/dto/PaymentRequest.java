package com.aiops.orderservice.dto;

/** What order-service sends to payment-service's POST /payments. */
public record PaymentRequest(String orderId, String customerId, double amount) {
}
