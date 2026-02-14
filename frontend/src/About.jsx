import React from 'react';

const About = () => {
    const teamMembers = [
        {
            name: 'PRADYUMNA RAY',
            rollNo: '2024CT05003',
            image: '/images/team/pradyumna.jpeg'
        },
        {
            name: 'ROHIT KUMAR DUBEY',
            rollNo: '2024CT05050',
            image: '/images/team/rohit.jpeg'
        },
        {
            name: 'SAMIRAN GHOSH',
            rollNo: '2023CT05033',
            image: '/images/team/samiran.png'
        },
        {
            name: 'TUSHAR GAJANAN LOKHANDE',
            rollNo: '2024CT05001',
            image: '/images/team/tushar.jpeg'
        }
    ];

    return (
        <div className="fade-in about-container">
            <div className="about-header">
                <img src="/images/team/college_icon.png" alt="BITS Pilani Logo" className="college-logo" />
                <div className="project-info">
                    <h2>Conversational AI Project</h2>
                    <p className="course-code">M.Tech AIML (S1-25_AMLCCZG521)</p>
                    <p className="semester">Semester 3</p>
                </div>
            </div>

            <div className="project-description">
                <h3>About This Project</h3>
                <p>
                    This B2B Chat Application was developed as part of the Conversational AI course assignment.
                    It integrates NLU, Dialog Management, and a responsive React frontend to simulate a
                    wholesale marketplace experience with intelligent chatbot support.
                </p>
            </div>

            <div className="team-section">
                <h3>Meet the Team</h3>
                <div className="team-grid">
                    {teamMembers.map((member, index) => (
                        <div key={index} className="team-card">
                            <div className="member-photo-container">
                                {member.placeholder ? (
                                    <div className="placeholder-photo">
                                        <span>{member.name.charAt(0)}</span>
                                    </div>
                                ) : (
                                    <img
                                        src={member.image}
                                        alt={member.name}
                                        className="member-photo"
                                        onError={(e) => {
                                            e.target.onerror = null;
                                            e.target.parentElement.innerHTML = `<div class="placeholder-photo"><span>${member.name.charAt(0)}</span></div>`;
                                        }}
                                    />
                                )}
                            </div>
                            <div className="member-info">
                                <h4 className="member-name">{member.name}</h4>
                                <p className="member-roll">{member.rollNo}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default About;
