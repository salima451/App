// src/app/services/hl7.service.ts

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Hl7Message {
  id: number;
  source: string;
  created_at: string;
  raw_preview: string;
}

export interface StatPoint {
  period: string;
  count: number;
}
// ✅ Remplacer l’ancienne interface
export interface PatientJourneyEvent {
  NSEJ:                     string;
  CBMRN:                    string;
  Resource:                 string;
  'Unité de soins'?:        string;
  'Service technique'?:     string;
  "Date/heure d'événement"?: string;
  "Date/heure de sortie"?: string; 
  "Temps passé"?:           string;
  "Temps passé en cours"?:  string;
  "Durée totale de séjour"?: string;
}

export interface PatientsResponse {
  patients: string[];
  total: number;
}

@Injectable({ providedIn: 'root' })  // ✅ Décorateur nécessaire
export class Hl7Service {
  public baseUrl = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  getPatients(source: string = 'both') {
    return this.http.get<{ total: number; patients: string[] }>(`${this.baseUrl}/patients?source=${source}`);
  }
  
  uploadFiles(files: File[]): Observable<{ results: any[] }> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    return this.http.post<{ results: any[] }>(`${this.baseUrl}/hl7/upload-multiple/`, formData);
  }

  getMessages(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/hl7/`);
  }

  launchParsing(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/hl7/parse-all`, {});
  }

  getWishMessages(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/wish/`);
  }

  getOrlineMessages(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/orline/`);
  }

  getPatientsList(source: string = 'both'): Observable<PatientsResponse> {
    return this.http.get<PatientsResponse>(`${this.baseUrl}/patients?source=${source}`);
  }
  

  clearAllTables() {
    return this.http.delete<any>(`${this.baseUrl}/clear-all/`);
  }

  processAllFiles() {
    return this.http.post(`${this.baseUrl}/process-all/`, {});
  }

  getMessagesByPatient(patientId: string, source: 'wish' | 'orline' | 'both' = 'both'): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/messages-by-patient/${encodeURIComponent(patientId)}?source=${source}`);
  }

  getSejoursByPatient(id_pat: string): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/patient/${id_pat}/sejours`);
  }

  getStats(interval: 'minute' | 'hour' | 'day' = 'hour'): Observable<StatPoint[]> {
    const params = new HttpParams().set('interval', interval);
    return this.http.get<StatPoint[]>(`${this.baseUrl}/hl7/stats`, { params });
  }
  getMessagesByPatientAndSejour(idPat: string, idSejour: string) {
    return this.http.get<any[]>(`${this.baseUrl}/messages-by-patient-sejour`, {
      params: {
        id_pat: idPat,
        id_sejour: idSejour
      }
    });
  }
  
  getStatsBetweenDates(startDate: string, endDate: string): Observable<StatPoint[]> {
    const params = new HttpParams()
      .set('start_date', startDate)
      .set('end_date', endDate);
    return this.http.get<StatPoint[]>(`${this.baseUrl}/hl7/stats-between-dates`, { params });
  }

  exportStatsExcel(interval: 'minute' | 'hour' | 'day' = 'hour'): void {
    const url = `${this.baseUrl}/hl7/stats/export?interval=${interval}`;
    window.open(url, '_blank');
  }

  getPatientIds(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/patients`);
  }
  getParcoursBySejour(patientId: string, sejourId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/journey/full/${patientId}/${sejourId}`);
  }
  
  getPatientJourney(patientId: string): Observable<PatientJourneyEvent[]> {
    return this.http.get<PatientJourneyEvent[]>(`${this.baseUrl}/patient-journey-gantt/${encodeURIComponent(patientId)}`);
  }
  
  clearDatabase(): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/clear-all/`);
  }
  getPatientCountsAdvanced(start: string, end: string): Observable<any> {
      return this.http.get(`${this.baseUrl}/tableaudebord/patient-counts-advanced-v2`, {
        params: {
          start_date: start,
          end_date: end
        }
      });
    }
}
