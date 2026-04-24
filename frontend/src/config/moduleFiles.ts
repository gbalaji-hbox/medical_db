import type { Module } from "@/api/types";

export interface FileSlot {
  field: string;        // multipart form field name
  label: string;        // display name
  required: boolean;
  accept: string;       // mime / extension hint
  sampleFile?: string;  // filename inside src/samples/{MODULE}/
  description?: string;
}

export const MODULE_FILE_SLOTS: Record<Module, FileSlot[]> = {
  mca: [
    {
      field: "patients_by_insurance",
      label: "Patients by Insurance",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "patients_by_insurance_sample.xlsx",
      description: "CGM APRIMA — patient insurance export",
    },
    {
      field: "patients_with_visits",
      label: "Patients With Visits by Insurance",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "patients_with_visits_sample.xlsx",
      description: "CGM APRIMA — visit history export",
    },
    {
      field: "patients_by_diagnosis",
      label: "Patients by Diagnosis / Medication",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "patients_by_diagnosis_sample.xlsx",
      description: "CGM APRIMA — diagnosis & medication export",
    },
    {
      field: "patient_list",
      label: "Patient List",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "patient_list_sample.xlsx",
      description: "CGM APRIMA — master patient list (includes ER contact notes)",
    },
    {
      field: "appointment_report",
      label: "Appointment Report",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "appointment_report_sample.xlsx",
      description: "CGM APRIMA — appointment schedule export",
    },
    {
      field: "copay_report",
      label: "Copay Report",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "copay_report_sample.xlsx",
      description: "CGM APRIMA — copay/billing export",
    },
    {
      field: "services_by_provider",
      label: "Services by Provider Summary",
      required: false,
      accept: ".xlsx,.xls",
      sampleFile: "services_by_provider_sample.xlsx",
      description: "Optional — provider utilisation summary",
    },
  ],
  hct: [
    {
      field: "patient_demographics",
      label: "Patient Demographics",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "patient-demographics_sample.xlsx",
      description: "NextGen — demographics export (FILTERS header row 1, data from row 5)",
    },
    {
      field: "patient_insurance",
      label: "Patient Insurance",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "patient-insurance_sample.xlsx",
      description: "NextGen — insurance export",
    },
    {
      field: "icd_codes",
      label: "ICD Codes (Location/Provider/Patient Wise)",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "HCT_Location_Wise_Provider_Wise_Patient_Wise_ICD_Codes_sample.xlsx",
      description: "NextGen — ICD code charge history, 12×Diag columns",
    },
  ],
  ssc: [
    {
      field: "chronic_management",
      label: "Chronic Management Patient Details",
      required: true,
      accept: ".csv",
      sampleFile: "Chronic_Management_Patient_Details_sample.csv",
      description: "Athena Health — chronic care management CSV (REPORT NAME in row 1)",
    },
    {
      field: "diagnosis_codes",
      label: "Patient Diagnosis Code",
      required: true,
      accept: ".csv",
      sampleFile: "Patient_Diagnosis_Code_sample.csv",
      description: "Athena Health — diagnosis codes CSV",
    },
    {
      field: "medications",
      label: "Patient Medications",
      required: true,
      accept: ".csv",
      sampleFile: "Patient_Medication_sample.csv",
      description: "Athena Health — medication list CSV",
    },
  ],
  cam: [
    {
      field: "data_new",
      label: "CAM Data File (data_new.xlsx)",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "data_new_sample.xlsx",
      description: "Epic Henry Ford — registry/problem list export (standard header row 1)",
    },
  ],
  cim: [
    {
      field: "final_hbox",
      label: "CIM Final HBox File",
      required: true,
      accept: ".xlsx,.xls",
      sampleFile: "final_hbox_sample.xlsx",
      description: "Epic Henry Ford — intensive care management export",
    },
  ],
  xhi: [
    {
      field: "emr_report",
      label: "EMR Final Report",
      required: true,
      accept: ".csv",
      sampleFile: "EMR_Final_Report_sample.csv",
      description: "DrChrono — EMR final report CSV",
    },
    {
      field: "medication_report",
      label: "Medication Report",
      required: true,
      accept: ".csv",
      sampleFile: "medication_report_sample.csv",
      description: "DrChrono — medication report CSV",
    },
    {
      field: "problem_report",
      label: "Problem Report",
      required: true,
      accept: ".csv",
      sampleFile: "problem_report_sample.csv",
      description: "DrChrono — problem list CSV",
    },
  ],
};
