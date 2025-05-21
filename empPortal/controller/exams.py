import fitz
import json
import logging
import openai
import os
import pdfkit
import re
import requests
import time
import zipfile
from django.utils.timezone import localtime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, authenticate, login ,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail, EmailMessage
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render,redirect, get_object_or_404
from django.template import loader
from django.template.loader import render_to_string
from django.utils.timezone import now
from empPortal.model import BankDetails
from fastapi import FastAPI, File, UploadFile
from pprint import pprint 

from ..models import Commission,Users, DocumentUpload, Branch, Exam, Question, Option, ExamResult, UserAnswer
from ..forms import DocumentUploadForm
from ..helpers import sync_user_to_partner, update_partner_by_user_id

logger = logging.getLogger(__name__)

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def members_exam(request):
    if request.user.is_authenticated:
        # Fetch user and bank details for the logged-in user
        user_details = Users.objects.get(id=request.user.id)  # Fetching the user's details
        if request.user.role_id == 4:
            if request.user.partner.partner_status == "3" or request.user.partner.partner_status == 3:
                if request.user.exam_eligibility == 1:
                    if request.user.exam_attempt <= 3:
                        if request.user.exam_pass == 0:
                             return render(request, 'exam/index.html', {
                                'user_details': user_details
                            })
                        else:
                            return redirect ('my-account')
                    else:
                        return redirect ('my-account')
                else:
                    return redirect ('my-account')
            else:
                return redirect ('my-account')
        else:
            return redirect ('my-account')
    else:
        return redirect('login')
    
def members_exam_mcq(request):
    if request.user.is_authenticated:
        # Fetch user and bank details for the logged-in user
        user_details = Users.objects.get(id=request.user.id)  # Fetching the user's details
        if request.user.role_id == 4:
            if request.user.partner.partner_status == "3" or request.user.partner.partner_status == 3:
                if request.user.exam_eligibility == 1:
                    if request.user.exam_attempt <= 3:
                        if request.user.exam_pass == 0:
                            exam_result_id = request.session.get('exam_result_id')
                            if(exam_result_id):
                                exam_result = ExamResult.objects.get(id=exam_result_id)
                                if exam_result.exam_submitted == 2:
                                    return redirect('my-account')  
                            exam_id = 1
                            exam = get_object_or_404(Exam, id=exam_id)
                            questions = Question.objects.filter(exam=exam).order_by('?').prefetch_related('options')  # Shuffle Questions
                            return render(request, 'exam/mcq.html', {'exam': exam, 'questions': questions})
        return redirect ('my-account')
    else:
        return redirect('login')


def start_exam(request):
    if request.user.is_authenticated:
        user_details = Users.objects.get(id=request.user.id)
        if (
            request.user.role_id == 4
            and request.user.partner.partner_status == '3'
            and request.user.exam_eligibility == 1
        ):
            if request.user.exam_attempt <= 3 and request.user.exam_pass == 0:
                user_details.exam_attempt += 1
                user_details.save(update_fields=['exam_attempt'])
                exam_id = 1
                exam = get_object_or_404(Exam, id=exam_id)
                
                exam_result = ExamResult.objects.create(
                    user_id=request.user.id,
                    exam=exam,
                    total_questions=0,
                    correct_answers=0,
                    percentage=0,
                )
                
                request.session['exam_result_id'] = exam_result.id
                return redirect('members_exam_mcq')
            return redirect('my-account')
    else:
        return redirect('login')


def submit_exam(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            answers = data.get("answers", [])
            exam_id = 1
            exam = get_object_or_404(Exam, id=exam_id)
            questions = Question.objects.filter(exam=exam)
            answer_count = len(answers)
            correct_answers = 0
            ques_array = []
            for answer in answers:
                print("Processing:", answer)
                question_id = answer.get("question_id")
                selected_option_id = answer.get("selected_option")
                try:
                    question = Question.objects.get(id=question_id, exam=exam)
                    selected_option = Option.objects.get(id=selected_option_id, question_id=question_id)
                    UserAnswer.objects.create(
                        user_id=request.user.id,
                        exam_id=exam.id,
                        question_id=question_id,
                        selected_option_id=selected_option_id
                    )

                    if selected_option.is_correct:
                        correct_answers += 1

                except (Question.DoesNotExist, Option.DoesNotExist) as e:
                    print(f"Skipping invalid entry: {e}")
                    continue  # skip invalid question/option pairs
            total_questions = exam.exam_question_count
            percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            status = "passed" if percentage >= exam.exam_eligibility else "failed"
            if status == "passed":
                completed_at = localtime().replace(microsecond=0, tzinfo=None)
                update_partner_by_user_id(request.user.id, {"partner_status": "4", "exam_completed_at": completed_at}, request=request)

            exam_result_id = request.session.get('exam_result_id')
            if(exam_result_id):
                exam_result = ExamResult.objects.filter(id=exam_result_id).update(
                    total_questions=total_questions,
                    correct_answers=correct_answers,
                    percentage=percentage,
                    status=status,
                    total_attempted_questions=answer_count,
                    exam_submitted=2    
                )
            else:
                ExamResult.objects.create(
                user_id=request.user.id,
                exam=exam,
                total_questions=total_questions,
                correct_answers=correct_answers,
                total_attempted_questions=answer_count,
                percentage=percentage,
                status=status,
                exam_submitted=2
            )
            Users.objects.filter(id=request.user.id).update(
                exam_last_attempted_on = now(),
            )
            
            if(status == "passed"):
                Users.objects.filter(id=request.user.id).update(
                    exam_pass = 1,
                )

            return JsonResponse({
                "status": "success",
                "result": status,
                "percentage": percentage,
                "attempted_questions": answer_count,
                "correct_answers": correct_answers
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
