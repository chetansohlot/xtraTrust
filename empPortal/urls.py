from django.urls import path, include

from . import views,export
from . import views
from . import authenticationView
from .controller import commissions, profile,policy,Dashboard, Referral, globalController, helpAndSupport, Employee, leads, sellMotor, sellHealth, sellTerm, Franchises, Department, Branches, members, customers, quoteManagement, healthQuoteManagement, homeManagement, exams,SourceMaster,BQP,Credential
from .controller import reports, PolicyCommission, PolicyPayment, insurance, dispositions, common
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path

# for xtra trust
from .controller import clients

motor_patterns = [
    path('quote-management/', quoteManagement.index, name='quote-management'),
    path('quotation-mgmt/save-quotation-form/', quoteManagement.saveQuotationData, name='save-quotation-form'),
    path('fetch-customer/', quoteManagement.fetch_customer, name='fetch-customer'),
    path('fetch-vehicle-info/', quoteManagement.fetch_vehicle_info, name='fetch-vehicle-info'),
    path('download-quotation-pdf/<str:cus_id>/', quoteManagement.downloadQuotationPdf, name='download-quotation-pdf'),
    path('quote-management/create-quote', quoteManagement.create_or_edit, name='quote-management-create'),
    path('quote-management/<str:customer_id>/', quoteManagement.create_or_edit, name='quote-management-edit'),
    path('quote-management/create-quote-vehicle-info/<str:cus_id>/', quoteManagement.createVehicleInfo, name='create-vehicle-info'),
    path('quote-management/show-quotation-info/<str:cus_id>/', quoteManagement.showQuotation, name='show-quotation-info'),
    path('send-quotation-email/<str:cus_id>/', quoteManagement.sendQuotationPdfEmail, name='send-quotation-email'),
]

health_patterns = [
    path('quote-management/', healthQuoteManagement.index, name='health-quote-management'),
    path('fetch-customer/', healthQuoteManagement.fetch_customer, name='health-fetch-customer'),
    path('fetch-vehicle-info/', healthQuoteManagement.fetch_vehicle_info, name='health-fetch-vehicle-info'),
    path('download-quotation-pdf/<str:cus_id>/', healthQuoteManagement.downloadQuotationPdf, name='health-download-quotation-pdf'),
    path('quote-management/create-quote', healthQuoteManagement.create_or_edit, name='health-quote-management-create'),
    path('quote-management/<str:customer_id>/', healthQuoteManagement.create_or_edit, name='health-quote-management-edit'),
    path('quote-management/create-quote-vehicle-info/<str:cus_id>/', healthQuoteManagement.createVehicleInfo, name='health-create-vehicle-info'),
    path('quote-management/show-quotation-info/<str:cus_id>/', healthQuoteManagement.showQuotation, name='health-show-quotation-info'),
]

urlpatterns = [
    # GLOBAL - SEARCH 
    path('global-search/', globalController.global_search, name='global_search'),
    # GLOBAL - SEARCH 


    path("login", authenticationView.login_view, name="login"),
    path("login-mobile", authenticationView.login_mobile_view, name="login-mobile"),
    path("check-email/", authenticationView.check_email, name="check-email"),
    path("check-mobile/", authenticationView.check_mobile, name="check-mobile"),
    path("register", authenticationView.register_view, name="register"),
    path("verify-otp", authenticationView.verify_otp_view, name="verify-otp"),
    path("register-verify-otp", authenticationView.register_verify_otp_view, name="register-verify-otp"),
    path("check-agent-existance/<str:uid>/", authenticationView.check_agent_existance, name="check-agent-existance"),
    path("verify-agent-existance", authenticationView.verify_agent_existance, name="verify-agent-existance"),
    path("re-send-otp-mobile-login", authenticationView.reSendOtp_View, name="re-send-otp-mobile-login"),
    path("mobile-verify-otp", authenticationView.mobile_verify_otp_view, name="mobile-verify-otp"),
    path("forget-password", authenticationView.forget_pass_view, name="forget-password"),
    path("reset-password", authenticationView.reset_pass_view, name="reset-password"),
    path("email-verify-otp", authenticationView.email_verify_otp, name="email-verify-otp"),
    path("resend-otp", authenticationView.verify_otp_view, name="resend-otp"),
    path("forget-resend-otp", authenticationView.forgetReSendOtp_View, name="forget-resend-otp"),
    path("register-resend-otp", authenticationView.registerReSendOtp_View, name="register-resend-otp"),
    
    path('user-and-roles/', views.userAndRoles, name='user-and-roles'),
    path('', homeManagement.index, name='home-index'),
    path('dashboard/', Dashboard.dashboard, name='dashboard'),
    path('business_summary_insurer_chartajax/', Dashboard.business_summary_insurer_chartajax, name='business_summary_insurer_chartajax'),
    path('business_consolidated_ajax/', Dashboard.business_consolidated_ajax, name='business_consolidated_ajax'),
    path('referral_summary_chartajax/', Dashboard.referral_summary_chartajax, name='referral_summary_chartajax'),
    path('partner_policy_summary_ajax/', Dashboard.partner_policy_summary_ajax, name='partner_policy_summary_ajax'),
    path('dashboard-ajax/', Dashboard.dashboard_ajax, name='dashboard_ajax'),
    path('business_summary_product_wiseajax/', Dashboard.business_summary_product_wiseajax,name='business_summary_product_wiseajax'),


    path('franchise-management/', Franchises.index, name='franchise-management'),
    # path('franchise-management/create-franchise', Franchises.create_or_edit, name='franchise-management-create'),
    # path('franchise-management/<str:franchise_id>/', Franchises.create_or_edit, name='franchise-management-edit'),
    path("toggle-franchise-status/<int:franchise_id>/", Franchises.franchise_toggle_status, name="franchise-toggle-status"), #Anjali
    path('franchise-management/create-franchise/', Franchises.franchise_basic_info, name='franchise-management-create'),
    path('franchise-management/create-franchise/<str:franchise_id>/', Franchises.franchise_basic_info, name='franchise-management-edit'),
    path('franchise-management/<str:franchise_id>/contact_info/', Franchises.franchise_contact_info, name='franchise-management-contact-info'),
    path('franchise-management/<str:franchise_id>/address-detail/', Franchises.franchise_address_details, name='franchise-management-address-details'),
    path('franchise-management/<str:franchise_id>/regulatory-compliance/', Franchises.franchise_regulatory_compliance, name='franchise-management-regulatory-compliance'),
    path('franchise-management/<str:franchise_id>/banking-detail/',Franchises.franchise_banking_details,name='franchise-management-banking-details'),



    path('branch-management/', Branches.index, name='branch-management'),
    path("check-branch-email/", Branches.check_branch_email, name="check-branch-email"),
    path('branch-management/create-branch', Branches.create_or_edit, name='branch-management-create'),
    path('branch-management/<str:branch_id>/', Branches.create_or_edit, name='branch-management-edit'),
    path('branch/toggle-status/<int:branch_id>/', Branches.toggle_branch_status, name='branch-toggle-status'),  #Anjali


    path('department-management/', Department.index, name='department-management'),
    path('department-management/create-department', Department.create_or_edit, name='department-management-create'),
    path('department-management/<str:department_id>/', Department.create_or_edit, name='department-management-edit'),
    path('department/toggle-status/<int:department_id>/', Department.toggle_department_status, name='department-toggle-status'),  #Anjali


    path('employee-management/', Employee.index, name='employee-management'),
    path('employee-management/create-employee', Employee.save_or_update_employee, name='employee-management-create'),
    path('employee-management/update-employee/<str:employee_id>/', Employee.save_or_update_employee, name='employee-management-update'),
    path('employee-management/view-employee/<str:employee_id>/', Employee.view_employee, name='employee-management-view'),
    path('employee-management/update-address/<str:employee_id>/', Employee.save_or_update_address, name='employee-management-update-address'),
    path('employee-management/family-details/<str:employee_id>/', Employee.save_or_update_family_details, name='employee-management-family-details'),
    path('employee-management/employment-info/<str:employee_id>/', Employee.save_or_update_employment_info, name='employee-management-employment-info'),
    path('employee-management/update-refrences/<str:employee_id>/', Employee.save_or_update_refrences, name='employee-management-update-refrences'),
    path('employee-management/update-allocation/<str:employee_id>/', Employee.update_allocation, name='employee-management-update-allocation'),
    path('employee-management/toggle-status/<str:employee_id>/<str:action>/', Employee.toggle_employee_status, name='employee-toggle-status'),

    path('employee-management/<str:employee_id>/', Employee.create_or_edit, name='employee-management-edit'),
    path('employee-management/employee-allocation-employee/<str:employee_id>', Employee.create_or_edit_allocation, name='employee-allocation-update'),
     
    path('v1/get-refferals-for-select',common.get_referrals,name="get-refferals-for-select"),
    path('v1/get-posp-for-select',common.get_posp,name="get-posp-for-select"),
    path('v1/get-branch-sales-managers',common.get_branch_sales_manager,name="get-branch-sales-managers"),
    path('v1/get-sales-teamleader',common.get_sales_team_leader,name="get-sales-teamleader"),
    path('v1/get-sales-relation-managers',common.get_sales_relation_manager,name="get-sales-relation-managers"),
    path('v1/fetch-vehicle-details/', common.fetch_vehicle_info, name='fetch-vehicle-details'),
    
    path('my-account/', profile.myAccount, name='my-account'),
    path('download-certificate-pdf/<str:cus_id>/', profile.downloadCertificatePdf, name='download-certificate'),

    path('upload-documents/', profile.upload_documents, name='upload_documents'),
    path("update-document/", profile.update_document, name="update_document"),
    path("update-document-id/", profile.update_document_id, name="update_document_id"),
    path('store-bank-data/', profile.storeOrUpdateBankDetails, name='store-bank-data'),
    path('store-allocation/', profile.storeAllocation, name='store-allocation'),
    
    path('get-branch-managers/', members.get_branch_managers, name='get_branch_managers'),
    path('get-sales-managers/', members.get_sales_managers, name='get_sales_managers'),
    path('get-rm-list/', members.get_rm_list, name='get_rm_list'),

    path("check-account-number/", profile.check_account_number, name="check-account-number"),

    path('update-user-details/', profile.update_user_details, name='update-user-details'),
    path('update-profile-image/', profile.update_profile_image, name='update-profile-image'),

    path("update-doc-status/", members.update_doc_status, name="update-doc-status"),  

    path('members/all-partner', members.members, name='members'),
    path('members/in-process', members.members_inprocess, name='members_inprocess'),
    path('members/document-pending-upload', members.members_document_pending_upload, name='members_document_pending_upload'),
    path('members/document-upload', members.members_document_upload, name='members_document_upload'),
    path('members/document-in-pending', members.members_document_inpending, name='members_document_inpending'),
    path('members/member-requested', members.members_requested, name='members_requested'),
    path('members/in-training', members.members_intraining, name='members_intraining'),
    path('members/in-exam', members.members_inexam, name='members_inexam'),
    path('exam', exams.members_exam, name='members_exam'),
    path('start-exam', exams.start_exam, name='start_exam'),
    path('exam/MCQs', exams.members_exam_mcq, name='members_exam_mcq'),
    path('exam/submit', exams.submit_exam, name='submit-exam'),
    path('members/activated', members.members_activated, name='members_activated'),
    path('members/rejected', members.members_rejected, name='members_rejected'),
    path('members/inactive', members.members_inactive, name='members_inactive'), ## members_inactive ##
    path('member/request-for-doc/<str:user_id>',members.requestForDoc, name='request-for-doc'),
    path('member/delete-member/<str:user_id>',members.deleteMember, name='delete-member'),
    path('member/member-view/<str:user_id>',members.memberView, name='member-view'),
    path('member/download-training-certificate/<str:user_id>',members.posTrainingCertificate, name='download-training-certificate'),
    path('member/download-certificate/<str:user_id>',members.posCertificate, name='download-certificate'),
    path('member/activate-user/<str:user_id>',members.activateUser, name='activate-user'),
    path('member/update-partner-status/<str:user_id>',members.updatePartnerStatus, name='update-partner-status'),
    path('member/login-activate-user/<str:user_id>',members.loginActivateUser, name='login-activate-user'),
    path('member/deactivate-user/<str:user_id>',members.deactivateUser, name='deactivate-user'),
    path('update-commission/', commissions.update_commission, name='update-commission'),
    path('add-partner/', members.add_partner, name='add-partner'),
    path('upload-partners/', members.upload_excel_users, name='upload-partners-excel'),
    path('member/v1/my-team',members.myTeamView,name="my-team"),
    
    # LEADS 
    path('lead-mgt/', leads.index, name='leads-mgt'),
    path('lead-mgt/create', leads.create_or_edit_lead, name='leads-mgt-create'),
    path('lead-mgt/<str:lead_id>/', leads.create_or_edit_lead, name='leads-mgt-edit'),
    path('lead-mgt/health-lead', leads.healthLead, name='health-lead'),
    path('lead-mgt/term-lead', leads.termlead, name='term-lead'),
    path('lead-mgt/lead-view/<int:lead_id>/', leads.viewlead, name='lead-view'),
    path('bulk-upload/', leads.bulk_upload_leads, name='bulk-upload-leads'),
    path('fetch-policy-details/', leads.fetch_policy_details, name='fetch-policy-details'),
    path('lead-mgt/export/', leads.export_leads_to_excel, name='lead_mgt_export'),
    path('get-state/', leads.get_state, name='get_state'),
    path('get-cities/', leads.get_cities, name='get_cities'),
    path('lead-mgt/product-info/lead-init/', leads.lead_init_view, name='lead-init'),
    path('lead-mgt/product-info/load-categories/', leads.load_categories, name='load-categories'),
    path('lead-mgt/product-info/load-products/', leads.load_products, name='load-products'),
    #path('lead-mgt/<str:lead_id>/', leads.view_lead, name='view_lead'),
    path('lead-mgt/v1/view/<str:lead_id>/', leads.view_lead, name='lead-view'),
    path('lead-mgt/basic_info/<str:lead_id>', leads.basic_info, name='basic-info'),
    path('lead-mgt/lead-source/<str:lead_id>',leads.lead_source, name='lead-source'),
    path('lead-mgt/lead-location/<str:lead_id>',leads.lead_location, name='lead-location'),
    path('lead-mgt/assignment/<str:lead_id>', leads.lead_assignment, name='lead-assignment'),
    path('lead-mgt/previous-policy-info/<str:lead_id>', leads.previous_policy_info, name='leads-previous-policy-info'),
    path('lead-mgt/v1/get-lead-activity-logs', leads.get_lead_activity_logs, name='get-lead-activity-logs'),

    path('leads/product-info/lead-init/<str:lead_id>', leads.lead_init_edit, name='edit-lead-init'),
    path('leads/v1/product-info/lead-allocation/<str:lead_id>', leads.lead_allocation, name='lead-allocation'),
    
    #save lead steps 
    path('lead-mgt/v1/save-lead-insurance-info',leads.save_leads_insurance_info,name="save-lead-insurance-info"), 
    path('leads/v1/udpate-lead-insurance-info',leads.update_leads_insurance_info,name="udpate-lead-insurance-info"), 
    path('leads/v1/save-lead-basic-info',leads.save_leads_basic_info,name="save-lead-basic-info"), 
    path('leads/v1/save-lead-source-info',leads.save_leads_source_info,name="save-lead-source-info"), 
    path('leads/v1/save-lead-location-info',leads.save_leads_location_info,name="save-lead-location-info"), 
    path('leads/v1/save-lead-assignment-info',leads.save_leads_assignment_info,name="save-lead-assignment-info"), 
    path('leads/v1/save-lead-allocation-info',leads.save_leads_allocation_info,name="save-lead-allocation-info"), 
    path('leads/v1/save-lead-previous-policy-info',leads.save_leads_previous_policy_info,name="save-lead-previous-policy-info"), 
    path('leads/v1/save-lead-motor-previous-policy-info',leads.save_leads_motor_previous_policy_info,name="save-lead-motor-previous-policy-info"), 
    
    path('leads/v1/save-lead-dispositions',leads.save_leads_dispositions,name="save-lead-dispositions"),
    #Insurance
    path('insurance-mgt/', insurance.insurance_list, name='insurance_index'),
    path('insurance-mgt/v1/create-insurance/', insurance.insurance_create, name='create-insurance'),
    path('insurance-mgt/v1/create-contact-details/<int:id>/', insurance.insurance_contact_details, name='create-contact-detail'),
    path('insurance-mgt/v1/edit/<int:insurance_id>/', insurance.insurance_edit, name='insurance_edit'),
    path('toggle-insurance-status/<int:insurance_id>/', insurance.toggle_insurance_status, name='insurance-toggle-status'),  #Anjali
    path('get-state/', insurance.get_state, name='get_state'),
    path('get-cities/', insurance.get_cities, name='get_cities'),

    # REFERRAL 
    path('referral-management/bulk-upload/', Referral.refBulkUpload, name='referral-bulk-upload'),
    path('referral-management/', Referral.index, name='referral-management'),
    path('referral-management/create-referral', Referral.create_or_edit, name='referral-management-create'),
    path('referral-management/<str:referral_id>/', Referral.create_or_edit, name='referral-management-edit'),
    path('referral/toggle-status/<int:referral_id>/', Referral.toggle_referral_status, name='referral-toggle-status'),
    path('referral/delete/<int:pk>/', Referral.soft_delete_referral, name='referral-soft-delete'),
    
    
    # path('referral-management/bulk-upload/', Referral.ref_bulk_upload, name='referral-bulk-upload'),

    # SELL-ONLINE 
        # MOTOR
        path('sell/motor', sellMotor.index, name='sell-motor'),
        path('sell/motor/motor-insurance', sellMotor.createMotorInsurance, name='create-motor-insurance'),
        path('sell/motor/motor-details', sellMotor.createMotorDetails, name='create-motor'),
        path('sell/motor/motor-proposal-basic-details', sellMotor.createMotorProposalBasicDetails, name='create-motor-proposal-basic'),
        path('sell/motor/motor-quote', sellMotor.createMotorQuote, name='create-motor-quote'),
        path('sell/motor/motor-proposal-nominee-details', sellMotor.createMotorProposalNomineeDetails, name='create-motor-proposal-nominee'),
        path('sell/motor/motor-proposal-address-details', sellMotor.createMotorProposalAddressDetails, name='create-motor-proposal-address'),
        path('sell/motor/motor-proposal-vehicle-details', sellMotor.createMotorProposalVehicleDetails, name='create-motor-proposal-vehicle'),
        path('sell/motor/motor-proposal-summary', sellMotor.createMotorProposalSummary, name='create-motor-proposal-summary'),
        # MOTOR


        # MOTOR 4W
        path('motor/4w/motor-insurance', sellMotor.create4wMotorInsurance, name='create-4w-motor-insurance'),
        path('motor/4w/motor-details', sellMotor.create4wMotorDetails, name='create-4w-motor'),
        path('motor/4w/motor-proposal-basic-details', sellMotor.create4wMotorProposalBasicDetails, name='create-4w-motor-proposal-basic'),
        path('motor/4w/motor-quote', sellMotor.create4wMotorQuote, name='create-4w-motor-quote'),
        path('motor/4w/motor-proposal-nominee-details', sellMotor.create4wMotorProposalNomineeDetails, name='create-4w-motor-proposal-nominee'),
        path('motor/4w/motor-proposal-address-details', sellMotor.create4wMotorProposalAddressDetails, name='create-4w-motor-proposal-address'),
        path('motor/4w/motor-proposal-vehicle-details', sellMotor.create4wMotorProposalVehicleDetails, name='create-4w-motor-proposal-vehicle'),
        path('motor/4w/motor-proposal-summary', sellMotor.create4wMotorProposalSummary, name='create-4w-motor-proposal-summary'),
        # MOTOR 4W

    path('sell/health', sellHealth.index, name='sell-health'),
    # HEALTH JOURNEY 
        path('health/health-insurance', sellHealth.createHealthInsurance, name='create-health-insurance'),
        path('health/health-quotes', sellHealth.createHealthQuotes, name='create-health-quotes'),
        path('health/health-proposer', sellHealth.createHealthProposer, name='create-health-proposer'),
        path('health/health-insured', sellHealth.createHealthInsured, name='create-health-insured'),
        path('health/health-history', sellHealth.createHealthHistory, name='create-health-history'),
        path('health/health-summary', sellHealth.createHealthSummary, name='create-health-summary'),
    # HEALTH JOURNEY 

    path('sell/term', sellTerm.index, name='sell-term'),
    # SELL-ONLINE 

    # REPORTS 
    path('report/commission-report/', export.commission_report, name='commission-report-v0'),
    path('report/a-business-report/', export.agent_business_report, name='agent-business-report-v0'),
    path('report/sm-business-report/', export.sales_manager_business_report, name='sales-manager-business-report-v0'),
    path('report/f-business-report/', export.franchisees_business_report, name='franchisees-business-report-v0'),
    path('report/i-business-report/', export.insurer_business_report, name='insurer-business-report-v0'),
    
    path('report/v1/comparison-report/', reports.commission_report, name='commission-report'),  
    path('report/v1/a-business-report/', reports.agent_business_report, name='agent-business-report'),
    path('report/v1/f-business-report/', reports.franchisees_business_report, name='franchisees-business-report'),
    path('report/v1/i-business-report/', reports.insurer_business_report, name='insurer-business-report'),
    path('report/v1/sm-business-report/', reports.sales_manager_business_report, name='sales-manager-business-report'),
    
    
    path('report/pending-insurer-commission-report/', reports.pending_insurer_commission_report, name='pending-insurer-commission-report'),
    path('report/pending-agent-commission-report/', reports.pending_agent_commission_report, name='pending-agent-commission-report'),
    
    # REPORTS 
    
    # EXPORT
    path('export-commission-report/', export.export_commission_data, name='export-commission-report-v0'),
    path('v1/export-comparison-report/', export.export_commission_data_v1, name='export-commission-report'),
    path('v1/export-sales-manager-business-report/', export.export_sales_manager_business_report, name='export-sales-manager-business-report'),
    path('v1/export-agent-business-report/', export.export_agent_business_report, name='export-agent-business-report'),
    path('v1/export-franchise-business-report/', export.export_franchise_business_report, name='export-franchise-business-report'),
    path('v1/export-insurer-business-report/', export.export_insurer_business_report, name='export-insurer-business-report'),


    # POLICY-COMMISION 
    path('policy-commission/agent-commission/', PolicyCommission.agent_commission, name='agent-commission'),
    path('policy-commission/logs-agent-commission/', PolicyCommission.logs_update_agent_commission, name='logs-agent-commission-update'),
    path('policy-commission/update-agent-commission/', PolicyCommission.update_agent_commission, name='update-agent-commission'),
    
    path('policy-commission/update-franchise-commission/', PolicyCommission.update_franchise_commission, name='update-franchise-commission'),
    path('policy-commission/franchisees-commission/', PolicyCommission.franchisees_commission, name='franchisees-commission'),
    path('policy-commission/logs-franchise-commission/', PolicyCommission.logs_update_franchise_commission, name='logs-franchise-commission-update'),
    
    path('policy-commission/insurer-commission/', PolicyCommission.insurer_commission, name='insurer-commission'),
    path('policy-commission/update-insurer-commission/', PolicyCommission.update_insurer_commission, name='update-insurer-commission'),
    path('policy-commission/logs-insurer-commission/', PolicyCommission.logs_update_insurer_commission, name='logs-insurer-commission-update'),
    
    # POLICY-COMMISION 

    # POLICY-PAYMENT 
    path('policy-payment/insurer-payment/', PolicyPayment.insurer_payment, name='insurer-payment'),
    path('policy-payment/get-campaign-log/', PolicyPayment.get_campaign_log, name='get-campaign-log'),
    path('policy-payment/view-payment-update-log/', PolicyPayment.view_payment_update_log, name='view-payment-update-log'),
    path("ajax/get-campaigns/", PolicyPayment.ajax_get_campaigns, name="ajax-get-campaigns"),
    # urls.py
    path('policy-payment/campaign-logs/<int:upload_id>/', PolicyPayment.campaign_policy_logs, name='campaign-policy-logs'),

    # POLICY-PAYMENT 
    

    # HELP-SUPPORT 
    path('help-and-support', helpAndSupport.index, name='help'),
    # HELP-SUPPORT 

    # MY-ACCOUNT 
    # MY-ACCOUNT 

    path('customers/', customers.customers, name='customers'),
    path('store-customer/', customers.store, name='store-customer'),
    path('customers/create', customers.create_or_edit, name='quotation-customer-create'),
    path('customers/<str:customer_id>/', customers.create_or_edit, name='quotation-customer-edit'),
    path('toggle-customer-status/<int:customer_id>/', customers.toggle_customer_status, name='customer-toggle-status'),  #Anjali

    path('motor/', include(motor_patterns)),
    path('health/', include(health_patterns)),
    
    path('commissions/', commissions.commissions, name='commissions'),
    path('add-commission/', commissions.create, name='add-commission'),
    path('store-commission/', commissions.store, name='store-commission'),

    path('billings/', views.billings, name='billings'),
    path('claim-tracker/', views.claimTracker, name='claim-tracker'),
    path('checkout/', views.checkout, name='checkout'),
    path('add-members/', views.addMember, name='add-members'),
    path('new-role/', views.newRole, name='new-role'),
    path('insert-role/', views.insertRole, name='insert-role'),
    path('create-user/', views.createUser, name='create-user'),
    path('get-users-by-role/', views.get_users_by_role, name='get_users_by_role'),
    path('get-users-by-role-id/', views.get_users_by_role_id, name='get_users_by_role_id'),
    path('get-team-leaders-by-manager/', views.get_team_leaders_by_manager, name='get_team_leaders_by_manager'),
    path('insert-user/', views.insertUser, name='insert-user'),
    path('role/edit/<str:id>',views.editRole, name='edit-role'),
    path('users/edit-user/<str:id>',views.editUser, name='edit-user'),
    path('users/edit-user-status',views.updateUserStatus, name='edit-user-status'),
    path('update-role/', views.updateRole, name='update-role'),
    path('update-user/', views.updateUser, name='update-user'),
    
    path('browser-policy/', policy.browsePolicy, name='browser-policy'),
    path('failed-policy-upload-view/<str:id>', views.failedPolicyUploadView, name='failed-policy-upload-view'),
    path('bulk-policies/<str:id>', policy.bulkPolicyView, name='bulk-policies'),
    # path('bulk-browser-policy/', views.bulkBrowsePolicy, name='bulk-browser-policy'),
    path('bulk-browser-policy/', policy.bulkBrowsePolicy, name='bulk-browser-policy'),
    path('policy-data/', policy.policyData, name='policy-data'),
    path('operator-verify-policy/', policy.operator_verify_policy, name='operator-verify-policy'),

    path('edit-policy-data/<str:id>', views.editPolicy, name='edit-policy'),
    path('view-policy-data/<str:id>', policy.viewPolicy, name='view-policy'),
    path('delete-policy-data/<str:id>', policy.deletePolicy, name='delete-policy'),
    path('edit-policy/<str:policy_id>/', policy.edit_policy, name='edit-policy-data'),
    re_path(r'^edit-policy-vehicle-details/(?P<policy_id>.+)/$', policy.edit_vehicle_details, name='edit-policy-vehicle-details'),
    re_path(r'^edit-policy-docs/(?P<policy_id>.+)/$', policy.edit_policy_docs, name='edit-policy-docs'),
    re_path(r'^edit-agent-payment-info/(?P<policy_id>.+)/$', policy.edit_agent_payment_info, name='edit-agent-payment-info'),
    re_path(r'^edit-insurer-payment-info/(?P<policy_id>.+)/$', policy.edit_insurer_payment_info, name='edit-insurer-payment-info'),
    re_path(r'^edit-franchise-payment-info/(?P<policy_id>.+)/$', policy.edit_franchise_payment_info, name='edit-franchise-payment-info'),

    path('update-policy/', views.updatePolicy, name='update-policy'),
    path('edit-bulk-policy/', policy.editBulkPolicy, name='edit-bulk-policy'),
    path('update-bulk-policies/', policy.updateBulkPolicy, name='update-bulk-policies'),
    path('bulk-update-logs/', policy.viewBulkUpdates, name='bulk-update-logs'),
    path('single-policy-log/', policy.viewSinglePolicyLog, name='single-policy-log'),
    path('bulk-policy-mgt/', policy.bulkPolicyMgt, name='bulk-policy-mgt'),
    path('policy-mgt/', policy.policyMgt, name='policy-mgt'),
    
    
    path('reprocess-bulk-policies',views.reprocessBulkPolicies,name="reprocess-bulk-policies"),
    path('continue-bulk-policies',views.continueBulkPolicies,name="continue-bulk-policies"),
    path('bulk-upload-logs/',policy.bulkUploadLogs,name='bulk-upload-logs'),
    
    path('change-password/',views.changePassword,name='change-password'),
    path('update-password',views.updatePassword,name='update-password'),
    path("logout/", views.userLogout, name="logout"),
    #  for creating of the export functionality 
    #  path('export-policy/', views.exportPolicies, name='update-policy'),
    path('export-policy/', export.exportPolicies, name='export-policy'),   
    #   path('check-relations/', export.check_related_policies, name='check-relation'),   

    
    #  for creating of the export functionality 
    #  path('export-policy/', views.exportPolicies, name='update-policy'),
    path('export-policy/', export.exportPolicies, name='export-policy'),   
    path('save-policy-data/', export.download_policy_data, name='save-policy-data'),


    ####  source master ---- parth url  ####
    path('source/',SourceMaster.source_list, name='source_list'),
    path('source/create/', SourceMaster.source_create, name='source_create'),
    path('source/edit/<int:source_id>/', SourceMaster.source_edit, name='source_edit'),
    path('source/delete/<int:source_id>/', SourceMaster.source_delete, name='source_delete'),
    
    ## BQP Url ##
    path('bqp/', BQP.bqp_list, name='bqp_list'),
    path('bqp/create/', BQP.bqp_create, name='bqp_create'),
    path('bqp/edit/<int:bqp_id>/', BQP.bqp_edit, name='bqp_edit'),
    path('bqp/delete/<int:bqp_id>/', BQP.bqp_delete, name='bqp_delete'),

    ## Credential URL ##
    path('credential/', Credential.credential_list,name='credential_list'),
    path('credential/create/', Credential.credential_create, name='credential_create'),
    path('credential/edit/<int:credential_id>/', Credential.credential_edit, name='credential_edit'),
    path('credential/delete/<int:credential_id>/toggle/', Credential.credential_delete, name='credential_delete'),

    path('get-pos-partners-by-bqp/', views.get_pos_partners_by_bqp,name="get-pos-partners-by-bqp"),
    
    path('disposition/v1/sub-disposition-list',dispositions.get_sub_disposition_list,name="get-sub-disposition"),
    
    path('clients/v1/index',clients.index,name="client-view")
]   


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)