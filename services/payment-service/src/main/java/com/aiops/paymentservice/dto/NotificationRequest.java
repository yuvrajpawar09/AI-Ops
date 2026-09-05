package com.aiops.paymentservice.dto;

/** What payment-service sends to notification-service's POST /notifications. */
public record NotificationRequest(String orderId, String customerId, String message) {
}
