package com.aiops.paymentservice.dto;

/** What notification-service's POST /notifications replies with. */
public record NotificationResponse(String notificationId, String status) {
}
