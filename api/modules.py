from django.shortcuts import render, redirect
from datetime import datetime, timedelta
from django.http import JsonResponse
from .mongoDb import get_collection
from django.contrib import messages
from bson import ObjectId, errors
from marshmallow import Schema, fields, validates, validate
from marshmallow.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from decouple import config
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
import uuid, json

products_collection = get_collection("products")
reviews_collection = get_collection("reviews")
users_collection = get_collection("users")
address_collection = get_collection("addresses")
orders_collection = get_collection("orders")
carts_collection = get_collection("carts")
coupons_collection = get_collection("coupons")
refund_requests_collection = get_collection("refund_requests")
