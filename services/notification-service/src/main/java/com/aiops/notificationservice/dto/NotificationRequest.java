package com.aiops.notificationservice.dto;

/** Body of POST /notifications, sent by payment-service. */
public record NotificationRequest(String orderId, String customerId, String message) {
}
