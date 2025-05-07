import { Component, OnInit } from '@angular/core';
import { CommonModule }       from '@angular/common';
import { FormsModule }        from '@angular/forms';
import { Hl7Service, PatientJourneyEvent }from '../services/hl7.service';
// filter-resource.pipe.ts
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'filterResource', pure: true })
export class FilterResourcePipe implements PipeTransform {
  transform(
    events: PatientJourneyEvent[],
    codes: string[]
  ): PatientJourneyEvent[] {
    return events.filter(e =>
      codes.some(c => e.Resource.startsWith(c))
    );
  }
}

@Component({
  selector: 'app-parcours',
  standalone: true,
  imports: [CommonModule, FormsModule, FilterResourcePipe],
  templateUrl: './parcourspatient.component.html',
  styleUrls: ['./parcourspatient.component.scss']
})
export class ParcoursComponent implements OnInit {
  patients:       string[]             = [];
  selectedPatient = '';
  journey:        PatientJourneyEvent[] = [];  // ← on utilise la bonne interface
  error:          string | null       = null;
  get filteredJourney(): PatientJourneyEvent[] {
    return this.journey.filter(e =>
      e.Resource.startsWith('A01') ||
      e.Resource.startsWith('A02') ||
      e.Resource.startsWith('A03')
    );
  }
  hasDischarge(): boolean {
    return this.journey.some(ev => ev.Resource.startsWith('A03'));
  }
  constructor(private hl7: Hl7Service) {}

  ngOnInit(): void {
    this.hl7.getPatientsList().subscribe({
      next: data => this.patients = data.patients,
      error: ()   => this.error    = 'Erreur lors du chargement des patients.'
    });
  }

  afficherParcours(): void {
    if (!this.selectedPatient) {
      this.error = 'Veuillez choisir ou entrer un identifiant patient.';
      return;
    }
    this.error = null;
    this.hl7.getPatientJourney(this.selectedPatient).subscribe({
      next: data => this.journey = data,       // OK, data: PatientJourneyEvent[]
      error: ()   => this.error = 'Aucun parcours trouvé pour ce patient.'
    });
  }

  getColor(resource: string): string {
    const map: Record<string, string> = {
      'A01 - ADMISSION': '#f5ae42',
      'A02 - TRANSFER':  '#48a9a6',
      'A03 - DISCHARGE': '#8cc152',
      Sortie:            '#8cc152'
    };
    return map[resource] || '#ffffff';
  }
}
