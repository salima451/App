import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Hl7Service, PatientsResponse } from '../services/hl7.service';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-messages',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './messages.component.html',
  styleUrls: ['./messages.component.scss']
})
export class MessagesComponent implements OnInit {
  messages: any[] = [];
  error: string | null = null;
  isLoading: boolean = false;

  patientId: string = '';
  selectedPatientId: string = '';
  sejoursPatient: string[] = [];
  selectedSejour: string = '';
  patientsList: string[] = [];
  totalPatients: number = 0;
  selectedSourceFilter: string = 'both';
  showPatientsSection: boolean = false;

  constructor(private hl7: Hl7Service) {}

  ngOnInit(): void {}

  goHome(): void {
    window.location.href = '/';
  }

  startParsing(): void {
    this.isLoading = true;
    this.hl7.processAllFiles().subscribe({
      next: () => {
        alert('✅ Parsing terminé avec succès !');
        this.isLoading = false;
      },
      error: (error: any) => {
        console.error("❌ Erreur parsing :", error);
        alert('❌ Erreur lors du parsing.');
        this.isLoading = false;
      }
    });
  }

  loadPatientsList(): void {
    this.hl7.getPatientsList(this.selectedSourceFilter).subscribe({
      next: (data: PatientsResponse) => {
        this.patientsList = data.patients;
        this.totalPatients = data.total;
        this.showPatientsSection = true;
      },
      error: (err) => {
        console.error("Erreur chargement patients", err);
      }
    });
  }

  loadPatientsWithFilter(): void {
    this.loadPatientsList();
  }

  loadWishMessages(): void {
    this.hl7.getWishMessages().subscribe({
      next: (data: any[]) => {
        this.messages = data.map(d => ({
          id: d.id,
          source: 'WISH',
          created_at: d.date_message || '-',
          raw_preview: JSON.stringify(d, null, 2)
        }));
      },
      error: (err: any) => {
        console.error("❌ Erreur WISH :", err);
        this.error = "Erreur chargement WISH.";
      }
    });
  }

  loadOrlineMessages(): void {
    this.hl7.getOrlineMessages().subscribe({
      next: (data: any[]) => {
        this.messages = data.map(d => ({
          id: d.id,
          source: 'ORLINE',
          created_at: d.date_message || '-',
          raw_preview: JSON.stringify(d, null, 2)
        }));
      },
      error: (err: any) => {
        console.error("❌ Erreur ORLINE :", err);
        this.error = "Erreur chargement ORLINE.";
      }
    });
  }

  clearAllMessages(): void {
    if (confirm("❗ Es-tu sûr de vouloir tout supprimer ?")) {
      this.hl7.clearAllTables().subscribe({
        next: () => {
          this.messages = [];
        },
        error: (err: any) => {
          console.error("❌ Erreur vidage tables :", err);
          this.error = "Erreur vidage tables.";
        }
      });
    }
  }

  rechercherMessages(): void {
    if (!this.patientId) {
      alert('Veuillez entrer un ID patient.');
      return;
    }

    this.isLoading = true;
    this.hl7.getMessagesByPatient(this.patientId).subscribe({
      next: (data) => {
        this.messages = [];

        if (data.wish_messages) {
          this.messages.push(...data.wish_messages.map((msg: any) => ({
            id: msg.id,
            source: 'WISH',
            created_at: msg.date_message || '-',
            raw_preview: JSON.stringify(msg, null, 2)
          })));
        }

        if (data.orline_messages) {
          this.messages.push(...data.orline_messages.map((msg: any) => ({
            id: msg.id,
            source: 'ORLINE',
            created_at: msg.date_message || '-',
            raw_preview: JSON.stringify(msg, null, 2)
          })));
        }

        this.isLoading = false;
      },
      error: (error) => {
        console.error('❌ Erreur récupération messages patient', error);
        this.isLoading = false;
        alert('Aucun message trouvé pour ce patient.');
      }
    });
  }

  rechercherSejours(): void {
    if (!this.selectedPatientId) return;
    this.hl7.getSejoursByPatient(this.selectedPatientId).subscribe({
      next: (data) => {
        this.sejoursPatient = data;
      },
      error: (err) => {
        console.error('Erreur chargement séjours', err);
        this.sejoursPatient = [];
      }
    });
  }

  loadMessagesBySejour(): void {
    if (!this.selectedPatientId || !this.selectedSejour) return;

    this.hl7.getMessagesByPatientAndSejour(this.selectedPatientId, this.selectedSejour)
      .subscribe({
        next: (messages) => {
          this.messages = messages.map(msg => ({
            id: msg.id,
            source: 'ORLINE',
            created_at: msg.date_message || '-',
            raw_preview: JSON.stringify(msg, null, 2)
          }));
        },
        error: (err) => {
          console.error("❌ Erreur chargement messages par séjour :", err);
          this.messages = [];
        }
      });
  }

  loadPatientMessages(patientId: string): void {
    this.patientId = patientId;
    this.rechercherMessages();
  }

  exportExcel(): void {
    window.open(`${this.hl7.baseUrl}/export/xlsx`, '_blank');
  }
}
