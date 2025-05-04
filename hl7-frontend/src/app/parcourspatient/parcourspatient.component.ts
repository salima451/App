import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms'; // ✅ Importer FormsModule
import { Hl7Service } from '../services/hl7.service';

@Component({
  selector: 'app-parcours',
  standalone: true, // ✅ Standalone
  templateUrl: './parcourspatient.component.html',
  styleUrls: ['./parcourspatient.component.scss'],
  imports: [CommonModule, FormsModule] // ✅ Ajout ici
})
export class ParcoursComponent implements OnInit {
  patients: string[] = [];
  selectedPatient: string = '';
  journey: any[] = [];
  error: string | null = null;
  getColor(resource: string): string {
    const colorMap: { [key: string]: string } = {
      'A01 - ADMISSION': '#a8e6cf',
      'A02 - TRANSFER': '#ff8b94',
      'A03 - DISCHARGE': '#dcedc1'
    };
    return colorMap[resource] || '#ffffff';
  }
  
  constructor(private hl7: Hl7Service) {}

  ngOnInit(): void {
    this.hl7.getPatientsList().subscribe({
      next: (data) => {
        this.patients = data.patients;
      },
      error: () => {
        this.error = 'Erreur lors du chargement des patients.';
      }
    });
  }

  afficherParcours() {
    if (!this.selectedPatient) {
      this.error = "Veuillez choisir ou entrer un identifiant patient.";
      return;
    }

    this.error = null;
    this.hl7.getPatientJourney(this.selectedPatient).subscribe({
      next: (data) => {
        this.journey = data;
      },
      error: () => {
        this.error = "Aucun parcours trouvé pour ce patient.";
      }
    });
  }

  getEventLabel(code: string): string {
    const map: Record<string, string> = {
      'A01 - ADMISSION': 'Admission',
      'A02 - TRANSFER': 'Transfer',
      'A03 - DISCHARGE': 'Discharge'
    };
    return map[code] || code;
  }
}
