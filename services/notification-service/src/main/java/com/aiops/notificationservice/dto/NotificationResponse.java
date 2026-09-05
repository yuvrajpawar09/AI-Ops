package com.aiops.notificationservice.dto;

/** Body returned by POST /notifications. */
public record NotificationResponse(String notificationId, String status) {
}
